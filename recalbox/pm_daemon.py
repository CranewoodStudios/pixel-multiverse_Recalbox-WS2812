#!/usr/bin/env python3
# pm_daemon.py — Event-driven LED daemon (FIFO version, auto-serial)
# Reads JSON lines from /tmp/pm.fifo and drives Plasma 2040 bridge:
#   frame = b"multiverse:data" + N*(B,G,R,br)

import os, sys, time, json, math, signal, select

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
FIFO_PATH = "/tmp/pm.fifo"
SYSTEMS_JSON = "/recalbox/share/pixel-multiverse/systems.json"
BUTTONS_JSON = "/recalbox/share/pixel-multiverse/buttons.json"
ES_STATE = "/tmp/es_state.inf"
HEADER = b"multiverse:data"
# --------------------------------

# pyserial (installed via pip --target /recalbox/share/pythonlibs)
USER_SITE = "/recalbox/share/pythonlibs"
if os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)
try:
    import serial   # type: ignore
except Exception as e:
    print("[pm] FATAL: pyserial not available:", e, flush=True)
    sys.exit(1)

running = True
def _stop(*_):
    global running
    running = False
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

def log(*a): print("[pm]", *a, flush=True)
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

def set_state(current_state, next_state, log_func=log):
    if states_equal(current_state, next_state):
        log_func("state unchanged:", state_label(next_state))
        return current_state
    log_func("state change:", state_label(current_state), "->", state_label(next_state))
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

def load_config():
    global _cfg
    try:
        with open(SYSTEMS_JSON, "r") as f:
            _cfg = json.load(f)
        log("loaded systems.json:", ",".join(sorted(_cfg.keys())))
    except Exception as e:
        log("systems.json not loaded:", e)
        _cfg = {}

def load_buttons_config():
    """Load button configuration from JSON file."""
    global _buttons_cfg, _coord_map, _pattern_queue, NUM_LEDS
    try:
        with open(BUTTONS_JSON, "r") as f:
            _buttons_cfg = json.load(f)
        btn_cfg = _buttons_cfg.get("buttons", {})
        
        # Update NUM_LEDS from config if specified
        if btn_cfg.get("enabled") and btn_cfg.get("num_leds"):
            NUM_LEDS = btn_cfg["num_leds"]
        
        # Parse led_map to create coord_map
        led_map = btn_cfg.get("led_map", [])
        _coord_map = {}
        for item in led_map:
            coord = tuple(item.get("coord", []))
            value = item.get("value")
            if coord and value is not None:
                _coord_map[coord] = value
        
        # Parse attract_program to create pattern_queue
        _pattern_queue = []
        for pattern_cfg in btn_cfg.get("attract_program", []):
            pattern = pattern_cfg.get("pattern")
            params = pattern_cfg.get("params", {})
            if pattern and params:
                _pattern_queue.append((pattern, params))
        
        log("loaded buttons.json:", f"{len(_coord_map)} LEDs mapped, {len(_pattern_queue)} patterns")
    except FileNotFoundError:
        log("buttons.json not found at", BUTTONS_JSON)
    except Exception as e:
        log("buttons.json not loaded:", e)

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
        yield cols; time.sleep(step_ms/1000)

def fade_all(from_lvl=40, to_lvl=0, ms_total=700):
    steps = max(1, int(ms_total/20))
    for s in range(steps+1):
        lvl = _clamp(int(lerp(from_lvl, to_lvl, s/steps)))
        yield solid(0,0,0,lvl); time.sleep(0.02)

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
    
    Note: time.sleep() is used intentionally within this generator to control
    animation timing. This is called from idle_attract() which runs in the main
    event loop and is designed to yield control at regular intervals.
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
    yield cols
    time.sleep(delay)
    
    # Determine iteration order based on direction
    if direction == 'left_to_right':
        for x in range(min_x, max_x + 1):
            for coord, led_idx in _coord_map.items():
                if coord[0] == x and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield cols
            time.sleep(delay)
    elif direction == 'right_to_left':
        for x in range(max_x, min_x - 1, -1):
            for coord, led_idx in _coord_map.items():
                if coord[0] == x and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield cols
            time.sleep(delay)
    elif direction == 'top_to_bottom':
        for y in range(min_y, max_y + 1):
            for coord, led_idx in _coord_map.items():
                if coord[1] == y and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield cols
            time.sleep(delay)
    elif direction == 'bottom_to_top':
        for y in range(max_y, min_y - 1, -1):
            for coord, led_idx in _coord_map.items():
                if coord[1] == y and led_idx < NUM_LEDS:
                    cols[led_idx] = color_on
            yield cols
            time.sleep(delay)

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
    yield cols
    time.sleep(delay)
    
    # Activate LEDs in order
    for angle, coord, led_idx in coord_angles:
        if led_idx < NUM_LEDS:
            cols[led_idx] = color_on
        yield cols
        time.sleep(delay)

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
    yield cols
    time.sleep(delay)
    
    # Group by distance and activate in steps
    current_distance = None
    for distance, coord, led_idx in coord_distances:
        # Round distance to group nearby LEDs
        rounded_distance = round(distance, 1)
        if current_distance != rounded_distance:
            current_distance = rounded_distance
            yield cols
            time.sleep(delay)
        if led_idx < NUM_LEDS:
            cols[led_idx] = color_on
    
    # Yield final frame with all LEDs activated
    yield cols

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
    
    dwell_sec = dwell_ms / 1000.0
    fade_sec = fade_ms / 1000.0
    
    # Initialize all LEDs to off
    cols = [(0, 0, 0, 0)] * NUM_LEDS
    
    # Iterate through each LED sequentially
    for led_idx in range(num_leds):
        if led_idx >= NUM_LEDS:
            break
        
        # Cycle through each color for this LED
        for color in colors:
            cols[led_idx] = color
            yield list(cols)  # Yield a copy, not the same list object
            time.sleep(dwell_sec)
    
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
        
        yield faded_cols
        time.sleep(fade_sec)

# ---------- event animations ----------
def anim_menu_pulse(ser, accent=None, seconds=2.0):
    base = accent if accent else default_menu_color()
    t0=time.monotonic()
    while (time.monotonic()-t0) < seconds:
        cols = breath_frame(time.monotonic(), color=base, speed=1.0, minf=0.3, maxf=0.9)
        send_colors(ser, cols); time.sleep(1.0/FPS)

def anim_game_start(ser, system_key=None, rom_key=None):
    layout = lookup_start_layout(system_key, rom_key)
    if layout:
        send_colors(ser, layout); time.sleep(1.0); return
    accent = system_accent(system_key) or (0,64,0,BRIGHT_LIMIT)
    for cols in wipe_frames(color=accent, step_ms=40): send_colors(ser, cols)
    send_colors(ser, solid(0,0,0,18)); time.sleep(0.25)

def anim_game_end(ser):
    for cols in wipe_frames(color=(64,0,0,BRIGHT_LIMIT), step_ms=40): send_colors(ser, cols)
    for cols in fade_all(from_lvl=28, to_lvl=10, ms_total=600): send_colors(ser, cols)

def anim_shutdown(ser):
    for _ in range(3):
        send_colors(ser, solid(0,0,0,BRIGHT_LIMIT)); time.sleep(0.08)
        send_colors(ser, solid(0,0,0,8)); time.sleep(0.1)
    for cols in fade_all(from_lvl=24, to_lvl=0, ms_total=900): send_colors(ser, cols)

def anim_reboot(ser):
    for cols in wipe_frames(color=(0,64,0,BRIGHT_LIMIT), step_ms=35): send_colors(ser, cols)
    for cols in wipe_frames(color=(64,0,0,BRIGHT_LIMIT), step_ms=35): send_colors(ser, cols)
    for cols in fade_all(from_lvl=28, to_lvl=0, ms_total=500): send_colors(ser, cols)

def anim_settings_changed(ser):
    col=(32,32,0,BRIGHT_LIMIT)
    for _ in range(3):
        send_colors(ser, solid(*col)); time.sleep(0.12)
        send_colors(ser, all_off());   time.sleep(0.08)

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
        log("mkfifo failed:", e)

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
    if env and os.path.exists(env):
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
            self.log("USB reconnect: no compatible serial device found; retrying in",
                     f"{self.reconnect_interval:.1f}s")
            return None

        try:
            self.ser = self.serial_factory(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
            self.port = port
            self.next_reconnect_at = 0.0
            self.log("USB connected:", port)
        except Exception as e:
            self.ser = None
            self.port = None
            self.next_reconnect_at = now + self.reconnect_interval
            self.log("USB connect failed for", port, ":", e)
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
                self.log("USB close failed:", e)
        if reason:
            self.log("USB disconnected:", old_port or "unknown port", "-", reason)
        else:
            self.log("USB disconnected:", old_port or "unknown port")

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
                self.log("USB close failed:", e)

# ---------- Main ----------
def main():
    load_config()
    load_buttons_config()
    ensure_fifo()

    usb = SerialConnection()
    output = FrameOutput(usb)
    log("daemon started; FIFO =", FIFO_PATH)

    current_state = make_state(STATE_MENU)
    current_idle = idle_for_state(current_state)
    last_idle = 0.0

    rdr, dummy_w = open_fifo_reader()
    poll = select.poll()
    poll.register(rdr, select.POLLIN)

    try:
        while running:
            usb.ensure_connection(time.monotonic())
            events = poll.poll(50)  # 50ms
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
                        except Exception:
                            evt = {}
                        name = (evt.get("event") or "").lower()

                        if name == "reload-config":
                            load_config()
                            load_buttons_config()

                        else:
                            syskey = get_system_key(evt)
                            romkey = get_rom_key(evt)

                            if name == "menu":
                                accent = system_accent(syskey)
                                anim_menu_pulse(output, accent=accent, seconds=2.0)
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)

                            elif name == "game-start":
                                anim_game_start(output, system_key=syskey, rom_key=romkey)
                                current_state = set_state(
                                    current_state,
                                    make_state(STATE_GAME_RUNNING, system_key=syskey, rom_key=romkey),
                                )
                                current_idle = idle_for_state(current_state)

                            elif name == "game-end":
                                anim_game_end(output)
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)

                            elif name == "shutdown":
                                anim_shutdown(output)
                                current_state = set_state(current_state, make_state(STATE_SHUTDOWN))
                                current_idle = idle_for_state(current_state)
                                send_state_frame(output, current_state)

                            elif name == "reboot":
                                anim_reboot(output)
                                current_state = set_state(current_state, make_state(STATE_REBOOT))
                                current_idle = idle_for_state(current_state)
                                send_state_frame(output, current_state)

                            elif name in ("settings-changed","controls-changed"):
                                anim_settings_changed(output)
                                send_state_frame(output, current_state)

                            elif name == "attract-on":
                                current_state = set_state(current_state, make_state(STATE_ATTRACT))
                                current_idle = idle_for_state(current_state)

                            elif name == "attract-off":
                                current_state = set_state(current_state, make_state(STATE_MENU, system_key=syskey))
                                current_idle = idle_for_state(current_state)

                            elif name == "solid":
                                b=int(evt.get("b",0)); g=int(evt.get("g",0)); r=int(evt.get("r",0)); br=int(evt.get("br",24))
                                current_state = set_state(
                                    current_state,
                                    make_state(STATE_SOLID, color=(b,g,r,br)),
                                )
                                current_idle = idle_for_state(current_state)
                                send_state_frame(output, current_state, fade=True)

                            elif name == "off":
                                current_state = set_state(current_state, make_state(STATE_OFF))
                                current_idle = idle_for_state(current_state)
                                send_state_frame(output, current_state, fade=True)

                        last_idle = 0.0  # next idle immediately

            now = time.monotonic()
            output.update(now)

            if current_idle is not None and now - last_idle >= (1.0/30.0):
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
        log("daemon stopped")

if __name__ == "__main__":
    main()
