#!/usr/bin/env bash
# =============================================================================
# Claude Code — single-component installer
#
# Deploys ONE new skill or agent (already scaffolded + registered in the dev
# tree by extend.py) into an existing ~/.claude installation, without the full
# wipe-and-recopy that install.sh performs. Re-syncs manifest.json and the
# prose docs the component touched, validates, and backs up first.
#
# Usage:
#   install-component.sh <skill|agent> <name> [--source DIR] [--target DIR] [--dry-run]
#
# Examples:
#   ./install-component.sh skill cost-forecaster
#   ./install-component.sh agent perf-analyst --dry-run
#   ./install-component.sh skill my-skill --source claude-code --target ~/.claude
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✔]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✘]${NC} $*"; exit 1; }

usage() {
  cat <<'EOF'
Usage: install-component.sh <skill|agent> <name> [options]

Deploy one new skill/agent (scaffolded by extend.py) into an existing
~/.claude installation. Re-syncs manifest.json + prose docs, backs up first.

Arguments:
  <skill|agent>    Component kind
  <name>           Component name (kebab-case)

Options:
  --source DIR     Dev tree to copy from   (default: claude-code)
  --target DIR     Install root to copy to (default: $HOME/.claude)
  --dry-run        Print actions; write nothing
  -h, --help       Show this help
EOF
  exit "${1:-0}"
}

# --- Argument parsing ----------------------------------------------------------
KIND=""
NAME=""
SOURCE_DIR=""
TARGET_DIR=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)  usage 0 ;;
    --dry-run)  DRY_RUN=1; shift ;;
    --source)   SOURCE_DIR="${2:-}"; shift 2 ;;
    --target)   TARGET_DIR="${2:-}"; shift 2 ;;
    skill|agent)
      if [[ -z "$KIND" ]]; then KIND="$1"; else err "Unexpected argument: $1"; fi
      shift ;;
    -*)         err "Unknown option: $1 (see --help)" ;;
    *)
      if [[ -z "$NAME" ]]; then NAME="$1"; else err "Unexpected argument: $1"; fi
      shift ;;
  esac
done

[[ -n "$KIND" ]] || { warn "Missing <skill|agent>"; usage 2; }
[[ -n "$NAME" ]] || { warn "Missing <name>"; usage 2; }

SOURCE_DIR="${SOURCE_DIR:-claude-code}"
TARGET_DIR="${TARGET_DIR:-$HOME/.claude}"
BACKUP_DIR="$TARGET_DIR/backup-$(date +%Y%m%d-%H%M%S)"

# --- Helpers (mirrors install.sh) ---------------------------------------------
BACKED_UP=()   # parallel arrays: original path -> backup copy path
BACKED_FROM=()

backup_if_exists() {
  local target="$1"
  if [[ -e "$target" ]]; then
    mkdir -p "$BACKUP_DIR"
    cp -r "$target" "$BACKUP_DIR/"
    BACKED_UP+=("$target")
    BACKED_FROM+=("$BACKUP_DIR/$(basename "$target")")
    warn "Backed up $(basename "$target") → $BACKUP_DIR/"
  fi
}

restore_backups() {
  local i
  for i in "${!BACKED_UP[@]}"; do
    rm -rf "${BACKED_UP[$i]}"
    cp -r "${BACKED_FROM[$i]}" "${BACKED_UP[$i]}"
  done
  warn "Restored ${#BACKED_UP[@]} file(s) from $BACKUP_DIR/"
}

# --- Preconditions ------------------------------------------------------------
[[ -d "$SOURCE_DIR" ]] || err "Source tree '$SOURCE_DIR' not found (pass --source)."
[[ -f "$SOURCE_DIR/manifest.json" ]] || err "No manifest.json in '$SOURCE_DIR'."
[[ -f "$TARGET_DIR/manifest.json" ]] || \
  err "No existing installation at '$TARGET_DIR' (no manifest.json). Run ./install.sh first."

if [[ "$KIND" == "skill" ]]; then
  SRC_PATH="$SOURCE_DIR/skills/$NAME"
  DST_PATH="$TARGET_DIR/skills/$NAME"
  [[ -f "$SRC_PATH/SKILL.md" ]] || err "Skill '$NAME' not found at $SRC_PATH/SKILL.md."
  MANIFEST_KEY="skills"
else
  SRC_PATH="$SOURCE_DIR/agents/$NAME.md"
  DST_PATH="$TARGET_DIR/agents/$NAME.md"
  [[ -f "$SRC_PATH" ]] || err "Agent '$NAME' not found at $SRC_PATH."
  MANIFEST_KEY="agents"
fi

# Component must already be registered in the source manifest (extend.py does this).
if ! python3 -c "
import json, sys
m = json.load(open('$SOURCE_DIR/manifest.json'))
sys.exit(0 if any(e.get('name') == '$NAME' for e in m.get('$MANIFEST_KEY', [])) else 1)
" 2>/dev/null; then
  err "'$NAME' is not registered in $SOURCE_DIR/manifest.json. Run extend.py first:
    python3 $SOURCE_DIR/skills/_shared/python/extend.py $KIND $NAME --description \"…\""
fi

# --- Plan ---------------------------------------------------------------------
log "Installing $KIND '$NAME'"
echo "  source : $SRC_PATH"
echo "  target : $DST_PATH"
echo "  re-sync: manifest.json, agents/README.md, ARCHITECTURE.md"

if [[ "$DRY_RUN" -eq 1 ]]; then
  warn "[DRY-RUN] no files written. Would:"
  echo "  - cp ${SRC_PATH} → ${DST_PATH}"
  echo "  - cp ${SOURCE_DIR}/manifest.json → ${TARGET_DIR}/manifest.json"
  [[ -f "$SOURCE_DIR/agents/README.md" ]] && echo "  - cp ${SOURCE_DIR}/agents/README.md → ${TARGET_DIR}/agents/README.md"
  [[ -f "$SOURCE_DIR/ARCHITECTURE.md" ]] && echo "  - cp ${SOURCE_DIR}/ARCHITECTURE.md → ${TARGET_DIR}/ARCHITECTURE.md"
  exit 0
fi

# --- Backup the files we will overwrite ---------------------------------------
backup_if_exists "$DST_PATH"
backup_if_exists "$TARGET_DIR/manifest.json"
[[ -f "$SOURCE_DIR/agents/README.md" ]] && backup_if_exists "$TARGET_DIR/agents/README.md"
[[ -f "$SOURCE_DIR/ARCHITECTURE.md" ]] && backup_if_exists "$TARGET_DIR/ARCHITECTURE.md"

# --- Copy the component -------------------------------------------------------
if [[ "$KIND" == "skill" ]]; then
  mkdir -p "$TARGET_DIR/skills"
  rm -rf "$DST_PATH"
  cp -r "$SRC_PATH" "$TARGET_DIR/skills/"
else
  mkdir -p "$TARGET_DIR/agents"
  cp "$SRC_PATH" "$DST_PATH"
fi
log "Component files copied"

# --- Re-sync registry + prose docs that extend.py updated ---------------------
cp "$SOURCE_DIR/manifest.json" "$TARGET_DIR/manifest.json"
log "manifest.json synced"
if [[ -f "$SOURCE_DIR/agents/README.md" ]]; then
  cp "$SOURCE_DIR/agents/README.md" "$TARGET_DIR/agents/README.md"
fi
if [[ -f "$SOURCE_DIR/ARCHITECTURE.md" ]]; then
  cp "$SOURCE_DIR/ARCHITECTURE.md" "$TARGET_DIR/ARCHITECTURE.md"
fi

# --- Validate the installed manifest (roll back on failure) -------------------
VALIDATOR="$TARGET_DIR/skills/_shared/python/validate_manifest.py"
[[ -f "$VALIDATOR" ]] || VALIDATOR="$SOURCE_DIR/skills/_shared/python/validate_manifest.py"
if [[ -f "$VALIDATOR" ]]; then
  if python3 "$VALIDATOR" "$TARGET_DIR/manifest.json" >/dev/null 2>&1; then
    log "Installed manifest validates"
  else
    warn "Installed manifest FAILED validation — rolling back."
    restore_backups
    err "Rolled back. Inspect $SOURCE_DIR/manifest.json with: python3 $VALIDATOR $SOURCE_DIR/manifest.json"
  fi
else
  warn "validate_manifest.py not found — skipped manifest validation."
fi

log "Installed $KIND '$NAME' into $TARGET_DIR"
echo "  Backups (if any): $BACKUP_DIR/"
echo "  Verify drift with: ./install.sh --check"
