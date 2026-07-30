#!/usr/bin/env python3
# pm_daemon.py — Event-driven LED daemon (FIFO version, auto-serial)
# Reads JSON lines from /tmp/pm.fifo and drives Plasma 2040 bridge:
#   frame = b"multiverse:data" + N*(B,G,R,br)

import os, sys, time, json, math, signal, select, logging

# ---------- CONFIG ----------
NUM_LEDS = 7
ORDER = list(range(NUM_LEDS))      # change if your physical order differs
BRIGHT_LIMIT = 170                 # cap brightness (0..255)
FPS = 60
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 0.05
RECONNECT_INTERVAL = 2.0
FADE_FPS = 50
FIXED_STATE_FADE_MS = 350
IDLE_FPS = 30
FIFO_PATH = "/tmp/pm.fifo"
SYSTEMS_JSON = "/recalbox/share/pixel-multiverse/systems.json"
BUTTONS_JSON = "/recalbox/share/pixel-multiverse/buttons.json"
ES_STATE = "/tmp/es_state.inf"
HEADER = b"multiverse:data"
# --------------------------------

def configure_logging():
    level_name = os.environ.get("PM_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="[pm] %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

configure_logging()

# pyserial (installed via pip --target /recalbox/share/pythonlibs)
USER_SITE = "/recalbox/share/pythonlibs"
if os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)
try:
    import serial   # type: ignore
except Exception as e:
    logging.getLogger("pm.daemon").error("pyserial not available: %s", e)
    sys.exit(1)

running = True
def _stop(*_):
    global running
    running = False
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

def log(*a, level=logging.INFO, category="daemon"):
    logging.getLogger("pm." + category).log(level, " ".join(str(x) for x in a))
def _clamp(x, lo=0, hi=255): return lo if x < lo else hi if x > hi else x
def lerp(a,b,t): return a + (b-a)*t

def pack_colors(cols):
    payload = bytearray()
    for (b,g,r,br) in cols:
        payload += bytes((_clamp(b), _clamp(g), _clamp(r), _clamp(br)))
    return HEADER + payload

def _mapped_colors(cols):
    mapped = [cols[src] if src < len(cols) else (0,0,0,0) for src in ORDER]
    return mapped

def send_colors(usb, cols):
    if hasattr(usb, "send_colors"):
        return usb.send_colors(cols)
    usb.write(pack_colors(_mapped_colors(cols))); usb.flush()
    return True

def all_off(): return [(0,0,0,0)] * NUM_LEDS
def solid(b,g,r,br): return [(b,g,r,_clamp(min(br,BRIGHT_LIMIT)))] * NUM_LEDS

def normalize_frame(cols):
    frame = list(cols[:NUM_LEDS])
    while len(frame) < NUM_LEDS:
        frame.append((0,0,0,0))
    return frame

def blend_frames(start_frame, target_frame, t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    frame = []
    for start, target in zip(normalize_frame(start_frame), normalize_frame(target_frame)):
        sb,sg,sr,sbr = start
        tb,tg,tr,tbr = target
        frame.append((
            _clamp(int(lerp(sb, tb, t))),
            _clamp(int(lerp(sg, tg, t))),
            _clamp(int(lerp(sr, tr, t))),
            _clamp(int(lerp(sbr, tbr, t))),
        ))
    return frame

class FrameOutput:
    def __init__(self, usb, fps=FADE_FPS):
        self.usb = usb
        self.fps = fps
        self.current_frame = all_off()
        self.fade = None
        self.next_update_at = 0.0

    def _send(self, cols):
        frame = normalize_frame(cols)
        if frame == self.current_frame and getattr(self.usb, "last_frame", None) == frame:
            return True
        self.current_frame = frame
        return self.usb.send_colors(frame)

    def send_colors(self, cols):
        self.fade = None
        return self._send(cols)

    def start_fade(self, target_frame, ms_total=FIXED_STATE_FADE_MS, now=None):
        if now is None:
            now = time.monotonic()
        duration = max(0.001, ms_total / 1000.0)
        self.fade = {
            "start": list(self.current_frame),
            "target": normalize_frame(target_frame),
            "start_at": now,
            "duration": duration,
        }
        self.next_update_at = now

    def update(self, now=None):
        if self.fade is None:
            return False
        if now is None:
            now = time.monotonic()
        if now < self.next_update_at:
            return False

        elapsed = now - self.fade["start_at"]
        t = elapsed / self.fade["duration"]
        frame = blend_frames(self.fade["start"], self.fade["target"], t)
        self._send(frame)

        if t >= 1.0:
            self.fade = None
        else:
            self.next_update_at = now + (1.0 / self.fps)
        return True

STATE_MENU = "MENU"
STATE_GAME_RUNNING = "GAME_RUNNING"
STATE_ATTRACT = "ATTRACT"
STATE_SHUTDOWN = "SHUTDOWN"
STATE_REBOOT = "REBOOT"
STATE_OFF = "OFF"
STATE_SOLID = "SOLID"

def make_state(name, system_key="", rom_key="", color=None):
    return {
        "name": name,
        "system_key": system_key or "",
        "rom_key": rom_key or "",
        "color": color,
    }

def state_label(state):
    if not state:
        return "NONE"
    name = state.get("name", "UNKNOWN")
    system_key = state.get("system_key") or ""
    if system_key:
        return f"{name}({system_key})"
    return name

def states_equal(left, right):
    return (
        left and right and
        left.get("name") == right.get("name") and
        left.get("system_key") == right.get("system_key") and
        left.get("rom_key") == right.get("rom_key") and
        left.get("color") == right.get("color")
    )

def _call_log(log_func, *args, **kwargs):
    try:
        log_func(*args, **kwargs)
    except TypeError:
        log_func(*args)

def set_state(current_state, next_state, log_func=log):
    if states_equal(current_state, next_state):
        _call_log(log_func, "state unchanged:", state_label(next_state), category="state")
        return current_state
    _call_log(log_func, "state change:", state_label(current_state), "->", state_label(next_state), category="state")
    return next_state

def idle_for_state(state):
    name = state.get("name")
    if name == STATE_ATTRACT:
        return idle_attract(mode=default_attract_mode())
    if name in (STATE_MENU, STATE_GAME_RUNNING):
        return idle_menu(accent=system_accent(state.get("system_key")))
    return None

def fixed_frame_for_state(state):
    name = state.get("name")
    if name in (STATE_OFF, STATE_SHUTDOWN, STATE_REBOOT):
        return all_off()
    if name == STATE_SOLID:
        b,g,r,br = state.get("color") or (0,0,0,0)
        return solid(b,g,r,br)
    return None

def send_state_frame(usb, state, fade=False):
    frame = fixed_frame_for_state(state)
    if frame is not None:
        if fade and hasattr(usb, "start_fade"):
            usb.start_fade(frame)
        else:
            send_colors(usb, frame)

class TimedFramesAnimation:
    def __init__(self, frames, frame_ms=40, hold_last_ms=0):
        self.frames = [normalize_frame(frame) for frame in frames]
        self.frame_interval = max(0.001, frame_ms / 1000.0)
        self.hold_last = max(0.0, hold_last_ms / 1000.0)
        self.started_at = None
        self.last_index = None
        self.finished = False
        self.current_frame = None

    def update(self, now):
        if self.finished or not self.frames:
            self.finished = True
            return None
        if self.started_at is None:
            self.started_at = now
        elapsed = now - self.started_at
        index = int(elapsed / self.frame_interval)
        if index >= len(self.frames):
            end_at = (len(self.frames) - 1) * self.frame_interval + self.hold_last
            if elapsed >= end_at:
                self.finished = True
            index = len(self.frames) - 1
        if index == self.last_index:
            return None
        self.last_index = index
        self.current_frame = self.frames[index]
        return self.current_frame

    def is_finished(self):
        return self.finished

class MenuPulseAnimation:
    def __init__(self, accent=None, seconds=2.0, fps=FPS):
        self.base = accent if accent else default_menu_color()
        self.seconds = seconds
        self.frame_interval = 1.0 / fps
        self.started_at = None
        self.next_update_at = 0.0
        self.finished = False
        self.current_frame = None

    def update(self, now):
        if self.finished:
            return None
        if self.started_at is None:
            self.started_at = now
            self.next_update_at = now
        elapsed = now - self.started_at
        if elapsed >= self.seconds:
            self.finished = True
            return None
        if now < self.next_update_at:
            return None
        self.next_update_at = now + self.frame_interval
        self.current_frame = breath_frame(elapsed, color=self.base, speed=1.0, minf=0.3, maxf=0.9)
        return self.current_frame

    def is_finished(self):
        return self.finished

def _fade_level_frames(from_lvl, to_lvl, ms_total):
    return list(fade_all(from_lvl=from_lvl, to_lvl=to_lvl, ms_total=ms_total))

def repeat_frame(cols, seconds, fps=IDLE_FPS):
    repeats = max(1, int(round(seconds * fps)))
    frame = normalize_frame(cols)
    for _ in range(repeats):
        yield list(frame)

def make_game_start_animation(system_key=None, rom_key=None):
    layout = lookup_start_layout(system_key, rom_key)
    if layout:
        return TimedFramesAnimation([layout], frame_ms=1000, hold_last_ms=1000)
    accent = system_accent(system_key) or (0,64,0,BRIGHT_LIMIT)
    frames = list(wipe_frames(color=accent, step_ms=40))
    frames.append(solid(0,0,0,18))
    return TimedFramesAnimation(frames, frame_ms=40, hold_last_ms=250)

def make_game_end_animation():
    frames = list(wipe_frames(color=(64,0,0,BRIGHT_LIMIT), step_ms=40))
    frames.extend(_fade_level_frames(from_lvl=28, to_lvl=10, ms_total=600))
    return TimedFramesAnimation(frames, frame_ms=40)

def make_shutdown_animation():
    frames = []
    for _ in range(3):
        frames.append(solid(0,0,0,BRIGHT_LIMIT))
        frames.append(solid(0,0,0,8))
    frames.extend(_fade_level_frames(from_lvl=24, to_lvl=0, ms_total=900))
    return TimedFramesAnimation(frames, frame_ms=80)

def make_reboot_animation():
    frames = list(wipe_frames(color=(0,64,0,BRIGHT_LIMIT), step_ms=35))
    frames.extend(wipe_frames(color=(64,0,0,BRIGHT_LIMIT), step_ms=35))
    frames.extend(_fade_level_frames(from_lvl=28, to_lvl=0, ms_total=500))
    return TimedFramesAnimation(frames, frame_ms=35)

def make_settings_changed_animation():
    col = (32,32,0,BRIGHT_LIMIT)
    frames = []
    for _ in range(3):
        frames.append(solid(*col))
        frames.append(all_off())
    return TimedFramesAnimation(frames, frame_ms=100)

def read_es_state(path=ES_STATE):
    out = {}
    try:
        with open(path, "r") as f:
            for line in f:
                if "=" in line:
                    k,v = line.strip().split("=",1)
                    out[k.strip()] = v.strip()
    except Exception:
        pass
    return out

# ---------- systems.json ----------
_cfg = {}
_buttons_cfg = {}
_coord_map = {}
_pattern_queue = []

def _read_json_config(path, default_value):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        log(os.path.basename(path), "not found at", path, level=logging.WARNING, category="config")
        return default_value
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data

def _build_button_derived(buttons_cfg):
    btn_cfg = buttons_cfg.get("buttons", {})
    if btn_cfg and not isinstance(btn_cfg, dict):
        raise ValueError("buttons must be an object")

    num_leds = NUM_LEDS
    if btn_cfg.get("enabled") and btn_cfg.get("num_leds") is not None:
        num_leds = int(btn_cfg["num_leds"])
        if num_leds <= 0:
            raise ValueError("buttons.num_leds must be greater than zero")

    coord_map = {}
    led_map = btn_cfg.get("led_map", [])
    if led_map and not isinstance(led_map, list):
        raise ValueError("buttons.led_map must be a list")
    for item in led_map:
        if not isinstance(item, dict):
            raise ValueError("buttons.led_map entries must be objects")
        coord = tuple(item.get("coord", []))
        value = item.get("value")
        if coord and value is not None:
            led_idx = int(value)
            if led_idx < 0:
                raise ValueError("LED indexes must be non-negative")
            coord_map[coord] = led_idx

    pattern_queue = []
    attract_program = btn_cfg.get("attract_program", [])
    if attract_program and not isinstance(attract_program, list):
        raise ValueError("buttons.attract_program must be a list")
    for pattern_cfg in attract_program:
        if not isinstance(pattern_cfg, dict):
            raise ValueError("buttons.attract_program entries must be objects")
        pattern = pattern_cfg.get("pattern")
        params = pattern_cfg.get("params", {})
        if pattern and params:
            if not isinstance(params, dict):
                raise ValueError("pattern params must be objects")
            pattern_queue.append((pattern, params))

    return num_leds, list(range(num_leds)), coord_map, pattern_queue

def apply_runtime_config(systems_cfg, buttons_cfg, num_leds, order, coord_map, pattern_queue):
    global _cfg, _buttons_cfg, _coord_map, _pattern_queue, NUM_LEDS, ORDER
    _cfg = systems_cfg
    _buttons_cfg = buttons_cfg
    NUM_LEDS = num_leds
    ORDER = order
    _coord_map = coord_map
    _pattern_queue = pattern_queue

def reload_runtime_config():
    systems_cfg = _read_json_config(SYSTEMS_JSON, {})
    buttons_cfg = _read_json_config(BUTTONS_JSON, {})
    num_leds, order, coord_map, pattern_queue = _build_button_derived(buttons_cfg)
    apply_runtime_config(systems_cfg, buttons_cfg, num_leds, order, coord_map, pattern_queue)
    log("loaded systems.json:", ",".join(sorted(_cfg.keys())), category="config")
    log("loaded buttons.json:", f"{len(_coord_map)} LEDs mapped, {len(_pattern_queue)} patterns", category="config")
    return True

def reload_runtime_config_safely():
    try:
        reload_runtime_config()
        log("configuration reload complete", category="config")
        return True
    except Exception as e:
        log("configuration reload failed; keeping previous configuration:", e,
            level=logging.ERROR, category="config")
        return False

def get_system_key(evt):
    sysid = (evt.get("system") or "").lower()
    if sysid: return sysid
    st = read_es_state()
    return (st.get("SystemId") or st.get("System") or "").lower()

def get_rom_key(evt):
    rp = evt.get("rom") or evt.get("rompath") or ""
    if not rp:
        st = read_es_state(); rp = st.get("RomPath","")
    base = os.path.basename(rp); name,_ = os.path.splitext(base)
    return name

# ---------- frames ----------
def breath_frame(t, color=(0,0,255,40), speed=1.2, minf=0.2, maxf=1.0):
    bb,bg,br,bbr = color
    f = (math.sin(t*speed)+1.0)/2.0
    f = minf + (maxf-minf)*f
    return [(bb,bg,br,_clamp(int(bbr*f))) for _ in range(NUM_LEDS)]

def wipe_frames(color=(0,64,64,BRIGHT_LIMIT), step_ms=50):
    for i in range(NUM_LEDS):
        cols = all_off()
        for k in range(i+1): cols[k] = color
        yield cols

def fade_all(from_lvl=40, to_lvl=0, ms_total=700):
    steps = max(1, int(ms_total/20))
    for s in range(steps+1):
        lvl = _clamp(int(lerp(from_lvl, to_lvl, s/steps)))
        yield solid(0,0,0,lvl)

# ---------- layouts from config ----------
def cols_from_layout(layout):
    cols=[]
    for i in range(min(NUM_LEDS, len(layout))):
        item = layout[i]
        if isinstance(item, dict):
            r=int(item.get("r",0)); g=int(item.get("g",0)); b=int(item.get("b",0)); br=int(item.get("br",0))
            cols.append((b,g,r,_clamp(min(br,BRIGHT_LIMIT))))
        elif isinstance(item, str):
            s=item.strip(); br=64
            if ":" in s:
                s,brs = s.split(":",1)
                try: br=int(brs)
                except: br=64
            if s.startswith("#") and len(s)==7:
                r=int(s[1:3],16); g=int(s[3:5],16); b=int(s[5:7],16)
                cols.append((b,g,r,_clamp(min(br,BRIGHT_LIMIT))))
            else:
                cols.append((0,0,0,0))
        else:
            cols.append((0,0,0,0))
    while len(cols) < NUM_LEDS: cols.append((0,0,0,0))
    return cols

def lookup_start_layout(system_key, rom_key):
    syscfg = _cfg.get(system_key or "", {})
    if syscfg and "rom_overrides" in syscfg:
        ro = syscfg["rom_overrides"].get(rom_key or "", None)
        if ro and "start_layout" in ro: return cols_from_layout(ro["start_layout"])
    if syscfg and "start_layout" in syscfg: return cols_from_layout(syscfg["start_layout"])
    return None

def system_accent(system_key):
    syscfg = _cfg.get(system_key or "", {})
    c = syscfg.get("accent")
    if isinstance(c, dict):
        b=int(c.get("b",0)); g=int(c.get("g",0)); r=int(c.get("r",0)); br=_clamp(min(int(c.get("br",24)),BRIGHT_LIMIT))
        return (b,g,r,br)
    return None

def default_menu_color():
    d=_cfg.get("defaults",{}); c=d.get("menu_color")
    if isinstance(c, dict):
        b=int(c.get("b",0)); g=int(c.get("g",0)); r=int(c.get("r",0)); br=_clamp(min(int(c.get("br",24)),BRIGHT_LIMIT))
        return (b,g,r,br)
    return (0,32,64,28)

def default_attract_mode():
    d=_cfg.get("defaults",{}); return (d.get("attract") or "breath").lower()

# ---------- pattern generation functions ----------
def _pattern_linear(direction, color_on=(0,0,255,40), color_off=(0,0,0,0), delay=0.05):
    """
    Generate frames for linear patterns.
    
    :param direction: 'left_to_right', 'right_to_left', 'top_to_bottom', 'bottom_to_top'
    :param color_on: Color tuple (b,g,r,br) for activated LEDs (default: blue)
    :param color_off: Color tuple (b,g,r,br) for deactivated LEDs
    :param delay: Delay between steps in seconds
    
    Timing is controlled by the main daemon loop.
    """
    if not _coord_map:
        return  # No coordinate mapping available
    
    # Extract x and y values from coordinates
    x_values = sorted(set(coord[0] for coord in _coord_map.keys()))
    y_values = sorted(set(coord[1] for coord in _coord_map.keys()))
    
    if not x_values or not y_values:
        return
    
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    
    # Initialize all LEDs to off color
    cols = [color_off] * NUM_LEDS
    yield from repeat_frame(cols, delay)
    
    # Determine iteration order based on direction
    if direction == 'left_to_right':
        for x in range(min_x, max_x + 1):
            for coord, led_idx in _coord_map.items():
                if coord[0] == x and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield from repeat_frame(cols, delay)
    elif direction == 'right_to_left':
        for x in range(max_x, min_x - 1, -1):
            for coord, led_idx in _coord_map.items():
                if coord[0] == x and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield from repeat_frame(cols, delay)
    elif direction == 'top_to_bottom':
        for y in range(min_y, max_y + 1):
            for coord, led_idx in _coord_map.items():
                if coord[1] == y and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield from repeat_frame(cols, delay)
    elif direction == 'bottom_to_top':
        for y in range(max_y, min_y - 1, -1):
            for coord, led_idx in _coord_map.items():
                if coord[1] == y and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield from repeat_frame(cols, delay)

def _pattern_radial(direction, color_on=(0,0,255,40), color_off=(0,0,0,0), delay=0.05):
    """
    Generate frames for radial patterns (clockwise/anticlockwise).
    
    :param direction: 'clockwise' or 'anticlockwise'
    :param color_on: Color tuple (b,g,r,br) for activated LEDs (default: blue)
    :param color_off: Color tuple (b,g,r,br) for deactivated LEDs
    :param delay: Delay between steps in seconds
    """
    if not _coord_map:
        return
    
    # Calculate center of the playfield
    x_values = [coord[0] for coord in _coord_map.keys()]
    y_values = [coord[1] for coord in _coord_map.keys()]
    
    if not x_values or not y_values:
        return
    
    center_x = (min(x_values) + max(x_values)) / 2.0
    center_y = (min(y_values) + max(y_values)) / 2.0
    
    # Calculate angles for all coordinates
    coord_angles = []
    for coord, led_idx in _coord_map.items():
        dx = coord[0] - center_x
        dy = coord[1] - center_y
        angle = math.atan2(dy, dx)
        coord_angles.append((angle, coord, led_idx))
    
    # Sort by angle
    if direction == 'clockwise':
        coord_angles.sort(key=lambda x: x[0])
    else:  # anticlockwise
        coord_angles.sort(key=lambda x: x[0], reverse=True)
    
    # Initialize all LEDs to off color
    cols = [color_off] * NUM_LEDS
    yield from repeat_frame(cols, delay)
    
    # Activate LEDs in order
    for angle, coord, led_idx in coord_angles:
        if led_idx < NUM_LEDS:
            cols[led_idx] = color_on
        yield from repeat_frame(cols, delay)

def _pattern_circular(direction, color_on=(0,0,255,40), color_off=(0,0,0,0), delay=0.05):
    """
    Generate frames for circular patterns (outward/inward).
    
    :param direction: 'outward' or 'inward'
    :param color_on: Color tuple (b,g,r,br) for activated LEDs (default: blue)
    :param color_off: Color tuple (b,g,r,br) for deactivated LEDs
    :param delay: Delay between steps in seconds
    """
    if not _coord_map:
        return
    
    # Calculate center of the playfield
    x_values = [coord[0] for coord in _coord_map.keys()]
    y_values = [coord[1] for coord in _coord_map.keys()]
    
    if not x_values or not y_values:
        return
    
    center_x = (min(x_values) + max(x_values)) / 2.0
    center_y = (min(y_values) + max(y_values)) / 2.0
    
    # Calculate distances from center for all coordinates
    coord_distances = []
    for coord, led_idx in _coord_map.items():
        dx = coord[0] - center_x
        dy = coord[1] - center_y
        distance = math.hypot(dx, dy)
        coord_distances.append((distance, coord, led_idx))
    
    # Sort by distance
    if direction == 'outward':
        coord_distances.sort(key=lambda x: x[0])
    else:  # inward
        coord_distances.sort(key=lambda x: x[0], reverse=True)
    
    # Initialize all LEDs to off color
    cols = [color_off] * NUM_LEDS
    yield from repeat_frame(cols, delay)
    
    # Group by distance and activate in steps
    current_distance = None
    for distance, coord, led_idx in coord_distances:
        # Round distance to group nearby LEDs
        rounded_distance = round(distance, 1)
        if current_distance != rounded_distance:
            current_distance = rounded_distance
            yield from repeat_frame(cols, delay)
        if led_idx < NUM_LEDS:
            cols[led_idx] = color_on
    
    # Yield final frame with all LEDs activated
    yield from repeat_frame(cols, delay)

def _pattern_sequential_colors(num_leds=7, dwell_ms=500, fade_steps=60, fade_ms=20, brightness=255):
    """
    Generate frames for sequential color pattern (Picade Max startup sequence).
    Each LED flashes through Red → Green → Blue → White, then all fade to off.
    
    :param num_leds: Number of LEDs to animate (default: 7)
    :param dwell_ms: Milliseconds each color stays on per LED (default: 500)
    :param fade_steps: Number of fade steps for fade-out (default: 60)
    :param fade_ms: Milliseconds per fade step (default: 20)
    :param brightness: Maximum brightness level 0-255 (default: 255)
    """
    # Color sequence: Red, Green, Blue, White
    # Note: Color format is (B, G, R, brightness)
    colors = [
        (0, 0, 255, brightness),      # Red (BGR format)
        (0, 255, 0, brightness),      # Green
        (255, 0, 0, brightness),      # Blue
        (255, 255, 255, brightness),  # White
    ]
    
    # Initialize all LEDs to off
    cols = [(0, 0, 0, 0)] * NUM_LEDS
    
    # Iterate through each LED sequentially
    for led_idx in range(num_leds):
        if led_idx >= NUM_LEDS:
            break
        
        # Cycle through each color for this LED
        for color in colors:
            cols[led_idx] = color
            yield from repeat_frame(cols, dwell_ms / 1000.0)
    
    # After all LEDs complete, fade all to off
    # Create a snapshot of the final state
    final_cols = list(cols)
    
    for step in range(fade_steps + 1):
        fade_factor = 1.0 - (step / fade_steps)
        faded_cols = []
        
        for i in range(NUM_LEDS):
            if i < num_leds:
                b, g, r, br = final_cols[i]
                # Fade brightness proportionally
                faded_br = int(br * fade_factor)
                faded_cols.append((b, g, r, _clamp(faded_br)))
            else:
                faded_cols.append((0, 0, 0, 0))
        
        yield from repeat_frame(faded_cols, fade_ms / 1000.0)

def idle_menu(accent=None):
    base = accent if accent else default_menu_color()
    t0=time.monotonic()
    while True:
        yield breath_frame(time.monotonic()-t0, color=base, speed=0.8, minf=0.2, maxf=0.8)

def idle_attract(mode="breath"):
    """
    Generator for attract mode patterns.
    If JSON pattern queue is available, cycles through configured patterns.
    Otherwise, falls back to hardcoded breath or rainbow modes.
    """
    # Try to use JSON-configured patterns if available
    if _pattern_queue:
        pattern_funcs = {
            'linear': _pattern_linear,
            'radial': _pattern_radial,
            'circular': _pattern_circular,
            'sequential_colors': _pattern_sequential_colors,
        }
        
        pattern_idx = 0
        while True:
            pattern_name, params = _pattern_queue[pattern_idx]
            pattern_func = pattern_funcs.get(pattern_name)
            
            if pattern_func:
                # Generate frames from this pattern
                for cols in pattern_func(**params):
                    yield cols
            
            # Move to next pattern
            pattern_idx = (pattern_idx + 1) % len(_pattern_queue)
    
    # Fallback to original hardcoded modes
    else:
        t0=time.monotonic()
        if mode == "rainbow":
            while True:
                t=time.monotonic()-t0; cols=[]
                for i in range(NUM_LEDS):
                    hue = (t*0.05 + i/NUM_LEDS) % 1.0
                    h6 = hue*6.0; k=int(h6); f=h6-k; v=24; p=0; q=int(v*(1.0-f)); tt=int(v*f)
                    if   k==0: rgb=(v,tt,p)
                    elif k==1: rgb=(q,v,p)
                    elif k==2: rgb=(p,v,tt)
                    elif k==3: rgb=(p,q,v)
                    elif k==4: rgb=(tt,p,v)
                    else:      rgb=(v,p,q)
                    cols.append((rgb[0], rgb[1], rgb[2], 20))
                yield cols
        else:
            while True:
                yield breath_frame(time.monotonic()-t0, color=(0,0,0,28), speed=0.6, minf=0.15, maxf=0.6)

# ---------- FIFO helpers ----------
def ensure_fifo(path=FIFO_PATH):
    try:
        if os.path.exists(path):
            if not stat_is_fifo(path):
                os.remove(path)
        if not os.path.exists(path):
            os.mkfifo(path, 0o666)
            os.chmod(path, 0o666)
    except Exception as e:
        log("mkfifo failed:", e, level=logging.ERROR, category="fifo")

def stat_is_fifo(path):
    try:
        import stat
        m = os.stat(path).st_mode
        return stat.S_ISFIFO(m)
    except Exception:
        return False

def open_fifo_reader(path=FIFO_PATH):
    rfd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    rdr = os.fdopen(rfd, 'r', buffering=1)  # line-buffered
    dummy_w = open(path, 'w')               # keep writer to prevent EOF
    return rdr, dummy_w

# ---------- Auto-detect serial port ----------
def find_serial_port():
    # Allow override
    env = os.environ.get("PM_PORT")
    if env:
        return env
    byid = "/dev/serial/by-id"
    cand = []
    try:
        for name in os.listdir(byid):
            low = name.lower()
            if ("picade" in low or "pimoroni" in low or "max" in low):
                cand.append(os.path.join(byid, name))
    except Exception:
        pass
    # Prefer data interface (often -if01) then console (-if00)
    cand.sort(key=lambda p: (("if02" not in p), p))
    for p in cand:
        try:
            s = serial.Serial(p, 115200, timeout=0.1)
            s.close()
            return p
        except Exception:
            continue
    # Fallback to common ACM paths
    for p in ("/dev/ttyACM0", "/dev/ttyACM1"):
        if os.path.exists(p):
            try:
                s = serial.Serial(p, 115200, timeout=0.1); s.close(); return p
            except Exception:
                pass
    return None

class SerialConnection:
    def __init__(self, find_port=find_serial_port, serial_factory=serial.Serial, log_func=log,
                 reconnect_interval=RECONNECT_INTERVAL):
        self.find_port = find_port
        self.serial_factory = serial_factory
        self.log = log_func
        self.reconnect_interval = reconnect_interval
        self.ser = None
        self.port = None
        self.next_reconnect_at = 0.0
        self.last_frame = None

    def is_connected(self):
        return self.ser is not None

    def ensure_connection(self, now=None):
        if self.ser is not None:
            return self.ser
        if now is None:
            now = time.monotonic()
        if now < self.next_reconnect_at:
            return None

        port = self.find_port()
        if not port:
            self.next_reconnect_at = now + self.reconnect_interval
            _call_log(self.log, "USB reconnect: no compatible serial device found; retrying in",
                      f"{self.reconnect_interval:.1f}s", level=logging.DEBUG)
            return None

        try:
            self.ser = self.serial_factory(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
            self.port = port
            self.next_reconnect_at = 0.0
            _call_log(self.log, "USB connected:", port)
        except Exception as e:
            self.ser = None
            self.port = None
            self.next_reconnect_at = now + self.reconnect_interval
            _call_log(self.log, "USB connect failed for", port, ":", e, level=logging.WARNING)
            return None

        if self.last_frame is not None:
            self._write_frame(self.last_frame, remember=False)
        return self.ser

    def disconnect(self, reason=None, now=None):
        old_port = self.port
        ser = self.ser
        self.ser = None
        self.port = None
        if now is None:
            now = time.monotonic()
        self.next_reconnect_at = now + self.reconnect_interval
        if ser is not None:
            try:
                ser.close()
            except Exception as e:
                _call_log(self.log, "USB close failed:", e, level=logging.WARNING)
        if reason:
            _call_log(self.log, "USB disconnected:", old_port or "unknown port", "-", reason,
                      level=logging.WARNING)
        else:
            _call_log(self.log, "USB disconnected:", old_port or "unknown port", level=logging.WARNING)

    def _write_frame(self, cols, remember=True):
        if remember:
            self.last_frame = list(cols)
        ser = self.ensure_connection()
        if ser is None:
            return False
        try:
            ser.write(pack_colors(_mapped_colors(cols)))
            ser.flush()
            return True
        except Exception as e:
            self.disconnect(reason=e)
            return False

    def send_colors(self, cols):
        return self._write_frame(cols, remember=True)

    def close(self):
        ser = self.ser
        self.ser = None
        self.port = None
        if ser is not None:
            try:
                ser.close()
            except Exception as e:
                _call_log(self.log, "USB close failed:", e, level=logging.WARNING)

# ---------- Main ----------
def main():
    reload_runtime_config_safely()
    ensure_fifo()

    usb = SerialConnection(log_func=lambda *a: log(*a, category="usb"))
    output = FrameOutput(usb)
    log("daemon started; FIFO =", FIFO_PATH, category="daemon")

    current_state = make_state(STATE_MENU)
    current_idle = idle_for_state(current_state)
    active_animation = None
    last_idle = 0.0

    rdr, dummy_w = open_fifo_reader()
    poll = select.poll()
    poll.register(rdr, select.POLLIN)

    try:
        while running:
            usb.ensure_connection(time.monotonic())
            events = poll.poll(20)  # 20ms
            if events:
                try:
                    line = rdr.readline()
                except Exception:
                    line = ""
                if line:
                    line = line.strip()
                    if line:
                        try:
                            evt = json.loads(line)
                        except Exception as e:
                            log("malformed FIFO message ignored:", e, "line:", line,
                                level=logging.WARNING, category="fifo")
                            evt = {}
                        name = (evt.get("event") or "").lower()

                        if name == "reload-config":
                            if reload_runtime_config_safely():
                                current_idle = idle_for_state(current_state)
                                send_state_frame(output, current_state)

                        else:
                            syskey = get_system_key(evt)
                            romkey = get_rom_key(evt)

                            if name == "menu":
                                accent = system_accent(syskey)
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)
                                active_animation = MenuPulseAnimation(accent=accent, seconds=2.0)
                                log("started menu pulse", category="animation")

                            elif name == "game-start":
                                current_state = set_state(
                                    current_state,
                                    make_state(STATE_GAME_RUNNING, system_key=syskey, rom_key=romkey),
                                )
                                current_idle = idle_for_state(current_state)
                                active_animation = make_game_start_animation(system_key=syskey, rom_key=romkey)
                                log("started game-start animation", category="animation")

                            elif name == "game-end":
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)
                                active_animation = make_game_end_animation()
                                log("started game-end animation", category="animation")

                            elif name == "shutdown":
                                current_state = set_state(current_state, make_state(STATE_SHUTDOWN))
                                current_idle = idle_for_state(current_state)
                                active_animation = make_shutdown_animation()
                                log("started shutdown animation", category="animation")

                            elif name == "reboot":
                                current_state = set_state(current_state, make_state(STATE_REBOOT))
                                current_idle = idle_for_state(current_state)
                                active_animation = make_reboot_animation()
                                log("started reboot animation", category="animation")

                            elif name in ("settings-changed","controls-changed"):
                                active_animation = make_settings_changed_animation()
                                log("started settings notification animation", category="animation")

                            elif name == "attract-on":
                                current_state = set_state(current_state, make_state(STATE_ATTRACT))
                                current_idle = idle_for_state(current_state)
                                active_animation = None

                            elif name == "attract-off":
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)
                                active_animation = None

                            elif name == "solid":
                                b=int(evt.get("b",0)); g=int(evt.get("g",0)); r=int(evt.get("r",0)); br=int(evt.get("br",24))
                                current_state = set_state(
                                    current_state,
                                    make_state(STATE_SOLID, color=(b,g,r,br)),
                                )
                                current_idle = idle_for_state(current_state)
                                active_animation = None
                                send_state_frame(output, current_state, fade=True)

                            elif name == "off":
                                current_state = set_state(current_state, make_state(STATE_OFF))
                                current_idle = idle_for_state(current_state)
                                active_animation = None
                                send_state_frame(output, current_state, fade=True)

                        last_idle = 0.0  # next idle immediately

            now = time.monotonic()
            output.update(now)

            if active_animation is not None:
                frame = active_animation.update(now)
                if frame is not None:
                    send_colors(output, frame)
                    last_idle = now
                if active_animation.is_finished():
                    active_animation = None
                    log("animation finished", category="animation")
                    if current_idle is None:
                        send_state_frame(output, current_state)

            elif current_idle is not None and now - last_idle >= (1.0/30.0):
                try: cols = next(current_idle)
                except StopIteration:
                    current_state = set_state(current_state, make_state(STATE_MENU))
                    current_idle = idle_for_state(current_state)
                    cols = next(current_idle)
                send_colors(output, cols); last_idle = time.monotonic()

    finally:
        try:
            send_colors(output, all_off())
            usb.close()
        except Exception: pass
        try:
            poll.unregister(rdr); rdr.close(); dummy_w.close()
            if os.path.exists(FIFO_PATH): os.chmod(FIFO_PATH, 0o666)
        except Exception: pass
        log("daemon stopped", category="daemon")

if __name__ == "__main__":
    main()
