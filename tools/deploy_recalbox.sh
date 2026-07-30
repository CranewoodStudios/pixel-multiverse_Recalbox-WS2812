#!/bin/sh
set -eu

TARGET="/recalbox/share/pixel-multiverse"
FORCE_CONFIG=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: tools/deploy_recalbox.sh [--target DIR] [--force-config] [--dry-run]

Copies the recalbox/ runtime files into the flattened Recalbox layout:
  /recalbox/share/pixel-multiverse/

Existing buttons.json and systems.json are preserved by default. Use
--force-config to replace them after writing timestamped .bak copies.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || { echo "missing value for --target" >&2; exit 2; }
      TARGET="$2"
      shift 2
      ;;
    --force-config)
      FORCE_CONFIG=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SRC="$REPO_ROOT/recalbox"

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf 'DRY-RUN:'
    printf ' %s' "$@"
    printf '\n'
  else
    "$@"
  fi
}

copy_file() {
  src=$1
  dest=$2
  mode=${3:-}

  run cp "$src" "$dest"
  if [ -n "$mode" ]; then
    run chmod "$mode" "$dest"
  fi
}

copy_config() {
  name=$1
  src="$SRC/config/$name"
  dest="$TARGET/$name"

  if [ -e "$dest" ]; then
    ts=$(date +%Y%m%d-%H%M%S)
    backup="$dest.bak.$ts"
    run cp "$dest" "$backup"

    if [ "$FORCE_CONFIG" -eq 1 ]; then
      copy_file "$src" "$dest" 0644
      echo "updated $dest after backup: $backup"
    else
      echo "preserved existing $dest; backup written: $backup"
      echo "repository default left at: $src"
    fi
  else
    copy_file "$src" "$dest" 0644
    echo "installed $dest"
  fi
}

[ -d "$SRC" ] || { echo "missing runtime source directory: $SRC" >&2; exit 1; }

run mkdir -p "$TARGET"

copy_file "$SRC/pm_daemon.py" "$TARGET/pm_daemon.py" 0755
copy_file "$SRC/pmctl" "$TARGET/pmctl" 0755

copy_config buttons.json
copy_config systems.json

for script in "$SRC"/scripts/*.sh; do
  [ -e "$script" ] || continue
  copy_file "$script" "$TARGET/$(basename "$script")" 0755
done

echo "deployment target: $TARGET"
