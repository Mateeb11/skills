#!/usr/bin/env bash
# mac-disk-cleanup scanner — READ-ONLY. Finds reclaimable disk space and prints
# it grouped by category. Deletes NOTHING. Safe to run anytime.
#
# Usage:
#   bash scan.sh                 # standard scan of caches, extensions, Docker, etc.
#   bash scan.sh --deep          # also scan common project dirs for node_modules / .venv
#   bash scan.sh --path <dir>    # add a custom dir to the project-artifact scan

set -u
DEEP=0
EXTRA_PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --deep) DEEP=1; shift ;;
    --path) EXTRA_PATHS+=("$2"); shift 2 ;;
    *) shift ;;
  esac
done

HOME_DIR="$HOME"
section() { printf '\n========== %s ==========\n' "$1"; }
# size in MB of a path (0 if missing)
mb() { [ -e "$1" ] && du -sm "$1" 2>/dev/null | cut -f1 || echo 0; }
# human-readable size line if path exists and is >= threshold MB
line() { local p="$1" min="${2:-1}"; local s; s=$(mb "$p"); [ "$s" -ge "$min" ] 2>/dev/null && printf '%6s MB  %s\n' "$s" "$p"; }

section "DISK OVERVIEW"
df -h /System/Volumes/Data 2>/dev/null | awk 'NR==1 || /Data/'

# ---------------------------------------------------------------------------
section "EDITOR EXTENSIONS — superseded old versions (SAFE — only the OLD ones)"
# For each extension family with >1 installed version, the editor uses only the
# HIGHEST version. List the specific OLDER version folders (with sizes) that are
# safe to delete. The current/highest version of each family must stay.
for extdir in "$HOME_DIR/.cursor/extensions" "$HOME_DIR/.vscode/extensions" "$HOME_DIR/.antigravity/extensions"; do
  [ -d "$extdir" ] || continue
  echo "# $extdir  (dir total: $(du -sh "$extdir" 2>/dev/null | cut -f1))"
  reclaim=0
  # family name = folder with trailing -<version>... stripped (bash 3.2 compatible)
  for fam in $(ls "$extdir" 2>/dev/null | sed -E 's/-[0-9].*$//' | sort -u); do
    # all version folders for this family, version-sorted; all but the last are old
    vers_sorted=$(ls -d "$extdir/$fam"-[0-9]* 2>/dev/null | sort -V)
    count=$(printf '%s\n' "$vers_sorted" | grep -c .)
    [ "$count" -le 1 ] && continue
    keep=$(printf '%s\n' "$vers_sorted" | tail -1)
    echo "   $fam  → keep: $(basename "$keep")"
    printf '%s\n' "$vers_sorted" | head -n $((count - 1)) | while IFS= read -r old; do
      [ -n "$old" ] || continue
      printf '      OLD (safe): %5s MB  %s\n' "$(mb "$old")" "$(basename "$old")"
    done
    oldsum=$(printf '%s\n' "$vers_sorted" | head -n $((count - 1)) | while IFS= read -r old; do [ -n "$old" ] && mb "$old"; done | awk '{s+=$1} END{print s+0}')
    reclaim=$((reclaim + oldsum))
  done
  [ "$reclaim" -gt 0 ] && echo "   >> reclaimable from old versions here: ${reclaim} MB" || echo "   (no duplicate versions — nothing to reclaim)"
done

# ---------------------------------------------------------------------------
section "PACKAGE-MANAGER CACHES (SAFE — regenerate on demand)"
line "$HOME_DIR/.npm/_cacache"
line "$HOME_DIR/.npm/_npx"
line "$HOME_DIR/.gradle/caches"
line "$HOME_DIR/.cache/uv"
line "$HOME_DIR/.cache/pip"
line "$HOME_DIR/Library/Caches/pip"
line "$HOME_DIR/.pub-cache"
line "$HOME_DIR/Library/pnpm/store"
line "$HOME_DIR/Library/Caches/Homebrew"
line "$HOME_DIR/.cache/yarn"
line "$HOME_DIR/Library/Caches/CocoaPods"
line "$HOME_DIR/.cargo/registry"
line "$HOME_DIR/.m2/repository"

# ---------------------------------------------------------------------------
section "NVM — installed node versions (old ones SAFE to drop; KEEP the active one)"
if [ -d "$HOME_DIR/.nvm/versions/node" ]; then
  active="$(nvm current 2>/dev/null || node -v 2>/dev/null || echo '?')"
  ncount=$(ls -d "$HOME_DIR"/.nvm/versions/node/* 2>/dev/null | grep -c .)
  echo "# active: $active   (installed: $ncount)"
  if [ "$ncount" -le 1 ]; then
    echo "# ⚠️  Only one Node version is installed and it's the active one — DO NOT delete it (would break your toolchain)."
  fi
  du -sh "$HOME_DIR"/.nvm/versions/node/* 2>/dev/null | sort -rh | while IFS=$'\t' read -r sz path; do
    if printf '%s' "$path" | grep -q "/$active$"; then
      printf '%s\t%s   ← ACTIVE, KEEP\n' "$sz" "$path"
    else
      printf '%s\t%s   (old — safe to drop)\n' "$sz" "$path"
    fi
  done
fi

# ---------------------------------------------------------------------------
section "~/.cache subfolders (SAFE)"
[ -d "$HOME_DIR/.cache" ] && du -sh "$HOME_DIR"/.cache/* 2>/dev/null | sort -rh | head -15

# ---------------------------------------------------------------------------
section "~/Library/Caches — top items (mostly SAFE)"
[ -d "$HOME_DIR/Library/Caches" ] && du -sh "$HOME_DIR"/Library/Caches/* 2>/dev/null | sort -rh | head -20
echo "# NOTE: *.ShipIt folders = app-updater leftovers (SAFE). Browser caches = SAFE but close the app first."

# ---------------------------------------------------------------------------
section "iOS SIMULATORS (SAFE if you don't need their state)"
SIMDIR="$HOME_DIR/Library/Developer/CoreSimulator/Devices"
if [ -d "$SIMDIR" ]; then
  echo "# total: $(du -sh "$SIMDIR" 2>/dev/null | cut -f1)  — clean with: xcrun simctl delete unavailable (or all)"
  du -sh "$SIMDIR"/* 2>/dev/null | sort -rh | head -8
fi

# ---------------------------------------------------------------------------
section "CLAUDE DESKTOP / XCODE caches (SAFE — re-downloads)"
line "$HOME_DIR/Library/Application Support/Claude/vm_bundles"
line "$HOME_DIR/Library/Application Support/Claude/Cache"
line "$HOME_DIR/Library/Developer/Xcode/DerivedData"
line "$HOME_DIR/Library/Developer/Xcode/iOS DeviceSupport"
line "$HOME_DIR/Library/Developer/Xcode/Archives"

# ---------------------------------------------------------------------------
section "ELECTRON APP CACHES (SAFE — Cache/GPUCache subfolders only)"
ASDIR="$HOME_DIR/Library/Application Support"
if [ -d "$ASDIR" ]; then
  for app in discord Slack Notion Code Cursor Antigravity Figma Postman; do
    base="$ASDIR/$app"
    [ -d "$base" ] || continue
    tot=$(du -sm "$base/Cache" "$base/Code Cache" "$base/GPUCache" "$base/Service Worker/CacheStorage" 2>/dev/null | awk '{s+=$1} END{print s+0}')
    [ "$tot" -ge 50 ] 2>/dev/null && printf '%6s MB  %s (cache subfolders)\n' "$tot" "$app"
  done
fi

# ---------------------------------------------------------------------------
section "DOCKER (run 'docker system df' when Docker is up)"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    docker system df 2>/dev/null
    echo "# SAFE: build cache, dangling images. REVIEW: tagged images you built. NEVER prune --volumes without asking (they hold databases)."
  else
    echo "# Docker installed but not running. The disk image (reclaimable after pruning) is at:"
    line "$HOME_DIR/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw"
    echo "# Start Docker, then: docker builder prune -a -f; docker image prune -a; (it auto-compacts the .raw)"
  fi
fi

# ---------------------------------------------------------------------------
section "TRASH & ORPHANED TEMP FILES (SAFE)"
line "$HOME_DIR/.Trash"
echo "# Office/temp lock files (start with ~\$ or .~lock):"
find "$HOME_DIR/Documents" "$HOME_DIR/Desktop" "$HOME_DIR/Downloads" -maxdepth 2 \
  \( -name '~$*' -o -name '.~lock*' \) 2>/dev/null | head -20

# ---------------------------------------------------------------------------
section "PROJECT ARTIFACTS — node_modules / .venv (SAFE, rebuild w/ install)"
SCAN_DIRS=()
if [ "$DEEP" -eq 1 ]; then
  for d in "$HOME_DIR/Documents" "$HOME_DIR/Desktop" "$HOME_DIR/Developer" "$HOME_DIR/Projects" "$HOME_DIR/dev" "$HOME_DIR/code"; do
    [ -d "$d" ] && SCAN_DIRS+=("$d")
  done
fi
for p in "${EXTRA_PATHS[@]:-}"; do [ -n "$p" ] && [ -d "$p" ] && SCAN_DIRS+=("$p"); done

if [ "${#SCAN_DIRS[@]}" -eq 0 ]; then
  echo "# (skipped — pass --deep to scan ~/Documents, ~/Desktop, ~/Developer, etc., or --path <dir>)"
else
  echo "# scanning: ${SCAN_DIRS[*]}"
  echo "## node_modules (>50MB):"
  find "${SCAN_DIRS[@]}" -type d -name node_modules -prune 2>/dev/null | while read -r d; do
    s=$(du -sm "$d" 2>/dev/null | cut -f1); [ "$s" -ge 50 ] 2>/dev/null && printf '%6s MB  %s\n' "$s" "$(dirname "$d")"
  done | sort -rn
  nmtot=$(find "${SCAN_DIRS[@]}" -type d -name node_modules -prune 2>/dev/null -exec du -sm {} + | awk '{s+=$1} END{print s+0}')
  echo "## node_modules TOTAL: ${nmtot} MB"
  echo "## Python .venv:"
  find "${SCAN_DIRS[@]}" -type d -name '.venv' -prune 2>/dev/null | while read -r d; do
    s=$(du -sm "$d" 2>/dev/null | cut -f1); printf '%6s MB  %s\n' "$s" "$(dirname "$d")"
  done | sort -rn | head -25
  venvtot=$(find "${SCAN_DIRS[@]}" -type d -name '.venv' -prune 2>/dev/null -exec du -sm {} + | awk '{s+=$1} END{print s+0}')
  echo "## .venv TOTAL: ${venvtot} MB"
fi

# ---------------------------------------------------------------------------
section "BIG INDIVIDUAL FILES in Downloads (REVIEW — may be real data)"
[ -d "$HOME_DIR/Downloads" ] && find "$HOME_DIR/Downloads" -type f -size +200M 2>/dev/null -exec du -sh {} + | sort -rh | head -10

section "SCAN COMPLETE"
echo "Reminder: this was READ-ONLY. Nothing was deleted. Review with the user, then delete only what they approve."
