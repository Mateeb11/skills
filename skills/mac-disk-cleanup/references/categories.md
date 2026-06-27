# Cleanup categories — catalog, safe commands, and what to never touch

This is the detailed reference for `mac-disk-cleanup`. Each entry says **what it is**, the **correct way to clean it** (some need a real command, not a blind `rm`), the **safety tier**, and notes. Read the relevant entries before deleting.

General rules:
- If `rm -rf` reports "Permission denied" or "Directory not empty", run `chmod -R u+w <dir>` first, then retry. Read-only files inside caches (npm `_npx`, gradle, mintlify) commonly cause this.
- Anything root-owned or installed from the Mac App Store (has a `_MASReceipt`) needs the user's password. You cannot `sudo` non-interactively — tell the user to run `! sudo rm -rf "<path>"` themselves, or drag the app to the Trash.
- After deleting, re-measure and report actual space freed.

---

## 🟢 Safe — pure caches / duplicates / leftovers

### Editor extensions (duplicate old versions)
`~/.cursor/extensions`, `~/.vscode/extensions`, `~/.antigravity/extensions`
Editors load only the newest version of each extension; older `name-<oldversion>` folders are dead weight. Keep the highest version per extension family, delete the rest. Restart the editor afterward so it refreshes its list.

### npm cache
`~/.npm/_cacache` → `npm cache clean --force`
`~/.npm/_npx` → `rm -rf ~/.npm/_npx` (may need `chmod -R u+w` first)

### uv cache
`~/.cache/uv` → `uv cache clean` (handles hardlinks into venvs correctly; existing venvs keep working)

### gradle cache
`~/.gradle/caches` → `rm -rf ~/.gradle/caches` (re-downloads on next build; `chmod -R u+w` if needed)

### pnpm store
`~/Library/pnpm/store` → `pnpm store prune` (removes only packages not referenced by any project)

### pip cache
`~/Library/Caches/pip` and/or `~/.cache/pip` → `rm -rf` (or `pip cache purge`)

### Dart/Flutter
`~/.pub-cache` → `dart pub cache clean -f` (or `rm -rf ~/.pub-cache/hosted ~/.pub-cache/git`)

### Homebrew
`~/Library/Caches/Homebrew` → `brew cleanup -s` (also removes old Cellar versions; reports space freed)

### CocoaPods cache
`~/Library/Caches/CocoaPods` → `rm -rf` (or `pod cache clean --all`)

### App-updater leftovers (Squirrel/ToDesktop "ShipIt")
`~/Library/Caches/*.ShipIt`, `~/Library/Caches/*-updater` → `rm -rf` (downloaded update installers; fully safe)

### nvm old node versions
`~/.nvm/versions/node/<old>` → `rm -rf` the versions you don't use. Keep the active one (`nvm current`).

### Trash
`~/.Trash/*` → `rm -rf ~/.Trash/*` (only after confirming the user wants it emptied)

### Orphaned Office temp/lock files
Files named `~$*` or `.~lock*` → safe to delete (leftover when an app crashed)

### Claude Desktop / Xcode caches
`~/Library/Application Support/Claude/vm_bundles` (re-downloads when local-agent VM feature is next used)
`~/Library/Developer/Xcode/DerivedData` (rebuilds on next Xcode build)
`~/Library/Developer/Xcode/iOS DeviceSupport` (regenerates when device reconnects)

---

## 🟡 Safe but rebuilds / re-downloads (mild cost — mention it)

### node_modules
Any `node_modules` dir → `rm -rf`. Rebuild with `npm install` / `pnpm install` / `yarn` before next using that project. For many projects, list them and let the user pick which are inactive — don't assume. The biggest single win on most dev machines.

### Python virtual environments
`.venv` / `venv` dirs → `rm -rf`. Rebuild with `uv sync` / `pip install -r requirements.txt`.

### iOS simulators
`xcrun simctl delete unavailable` (removes sims for uninstalled runtimes — safe) or `xcrun simctl delete all` (wipes all simulator state). If `simctl` is missing (Command Line Tools only, no full Xcode), the device folders under `~/Library/Developer/CoreSimulator/Devices/` are orphaned and can be `rm -rf`'d directly.

### Electron app caches
`~/Library/Application Support/<app>/{Cache,Code Cache,GPUCache,Service Worker/CacheStorage}` for discord/Slack/Notion/etc. → `rm -rf` the cache subfolders only. Do NOT delete the parent app-support folder (it holds real data).

### Browser caches
Chrome/Firefox caches under `~/Library/Caches/<browser>` and `~/Library/Application Support/Google/Chrome/.../Cache` → safe, but close the browser first. Do NOT delete the browser **profile** (bookmarks, history, logins, extensions).

### Docker
Start Docker first (`open -a Docker`, wait for `docker info`). Then:
- Build cache (usually the biggest): `docker builder prune -a -f`
- Stopped containers: `docker container prune -f`
- Dangling images: `docker image prune -f`
- Unused tagged images (REVIEW — your own builds): `docker image prune -a` — confirm first; public images re-pull, local builds need rebuilding.
- The `Docker.raw` disk image auto-compacts after pruning (Apple Silicon). Quitting Docker helps it trim.
- **NEVER** `docker system prune --volumes` without explicit confirmation — volumes hold real databases.
- If you started Docker only to prune and it wasn't running before, quit it afterward to restore prior state.

---

## 🔴 Real data — review only, never delete without explicit specific confirmation

- `~/Documents`, `~/Desktop`, `~/Pictures`, `~/Movies`, `~/Music` actual files
- `.git` directories — project history
- Outlook/Mail local stores: `~/Library/Group Containers/*Office/Outlook`, `~/Library/Mail` — real email
- Docker **volumes** — databases
- App **profiles/databases** (not caches): Chrome/Notion/Slack profiles, password stores
- Photos library, iCloud Drive contents
- Android SDK (`~/Library/Android/sdk`), language runtimes, IDE app bundles — tools, not junk; only remove if the user says they don't need them
- Large files in `~/Downloads` — could be installers the user still wants; list and ask

When unsure whether something is data or cache, show it under 🔴 and ask the user what it is before doing anything.
