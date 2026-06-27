---
name: mac-disk-cleanup
description: Scan a Mac for reclaimable disk space — caches, duplicate editor extensions, package-manager caches (npm/gradle/uv/pnpm/Homebrew), Docker images and build cache, iOS simulators, node_modules and Python venvs, app caches, and old downloads — then present what was found grouped by size and safety, and let the USER choose what to delete. Use this skill whenever the user wants to free up disk space, clean up their Mac, says their disk is full or storage is low, asks "what can I delete", "what's taking up space", "clean my caches", or wants to reclaim gigabytes — even if they don't use the exact words "cleanup" or "cache". Always show findings before deleting and never delete real user data without explicit confirmation.
---

# Mac Disk Cleanup

Help the user reclaim disk space on macOS safely. The golden rule: **you find and show, the user decides.** Never delete anything the user hasn't explicitly approved, and only ever surface things that are genuinely safe to remove (caches, rebuildable artifacts, duplicates, leftovers) — never their actual documents, code, photos, mail, or app data.

## Core principles (read these first)

1. **Scan is read-only. Deletion is interactive.** The scan never deletes. After showing findings, ask the user what they want removed, then delete only those.
2. **Only surface SAFE-to-delete items.** Safe = regenerates automatically (caches), is rebuildable (node_modules, build output), is a duplicate, or is a leftover (old versions, updater installers, orphaned temp files). When something *holds real data* (databases, mail, project source, photos, volumes), either leave it out or clearly label it "🔴 real data — review only" and never delete it without an explicit, specific yes.
3. **Always show before deleting.** Present findings grouped by size and safety. Let the user see exactly what would go and how much it frees.
4. **The user has the call.** Use the AskUserQuestion tool to let them pick categories/folders. Default to the safest option. Never assume "delete everything."
5. **Ask when unsure.** If a folder's purpose or structure isn't clear (e.g. an unfamiliar app, an ambiguous project layout, something that might be real data), ask the user what it is before treating it as deletable. It's always better to ask than to delete something that mattered.
6. **Verify, don't claim.** After deleting, re-measure and report the actual space freed. Never report something as cleaned without confirming it's gone.

## Workflow

### Step 1: Run the scan

Run the bundled scanner — it's read-only and prints findings grouped by category with sizes:

```bash
bash <skill-path>/scripts/scan.sh
```

It accepts optional flags:
- `--deep` — also scans `~/Documents`, `~/Desktop`, `~/Developer`, and other common project locations for `node_modules` and Python `.venv` directories (slower, but finds the biggest wins).
- `--path <dir>` — scan an additional custom directory for project artifacts.

Start with a plain run; offer `--deep` if the user wants to go further or the plain run didn't find much.

### Step 2: Present the findings

Summarize what the scan found in a clear table grouped by **safety tier**, largest first. For each category give the size and a one-line "what it is / how it comes back". Show totals per tier.

**Use the script's exact numbers — do not estimate or eyeball counts.** The scanner prints precise counts and `TOTAL` lines (e.g. node_modules count, `.venv` count, per-dir reclaim totals). Quote those exact figures consistently everywhere you mention them — the table, the summary, and any self-report. Eyeballing leads to contradictory numbers across your message (saying "6 projects" in one place and "19" in another). If you need a count or total the script didn't print, compute it explicitly with a command rather than guessing.

Tiers to use:
- 🟢 **Safe** — pure caches, duplicates, leftovers, rebuildable artifacts. Recommend these freely.
- 🟡 **Safe but rebuilds / re-downloads** — node_modules, venvs, Docker images, browser caches. Fine to delete, mild cost (reinstall/re-pull, or close the app first).
- 🔴 **Real data — review only** — databases, mail, source code, volumes, photos. Show for awareness; do NOT offer to delete unless the user explicitly insists, and even then confirm specifically.

### Step 3: Let the user choose

Use the AskUserQuestion tool (multiSelect where appropriate) to let the user pick which categories or specific folders to delete. Put the safest / highest-value option first and mark it "(Recommended)". For project folders (node_modules/venv), if there are many, offer to list them so the user can pick which projects are inactive — don't assume.

See `references/categories.md` for the full catalog of locations, exactly how to clean each one safely (some need a proper command, not a blind `rm` — e.g. `uv cache clean`, `brew cleanup`, `docker` prunes, `pnpm store prune`), and the things to never touch.

### Step 4: Delete what they approved

- Use the correct removal method per category (see the reference — caches with hardlinks, Docker, App Store apps, etc. have special handling).
- Some files are read-only; if `rm -rf` reports "Permission denied" / "Directory not empty", `chmod -R u+w <dir>` first, then retry.
- App Store apps and anything root-owned need the user's password — you can't `sudo` non-interactively. Tell the user to run `! sudo rm -rf "<path>"` themselves (the `!` prefix runs it in-session so the password prompt works), or to drag the app to the Trash.
- For Docker, start Docker, prune, then quit it if it wasn't running before. Never prune `--volumes` without explicit confirmation — volumes hold real databases.

### Step 5: Verify and report

Re-measure each thing you deleted (or the parent dir) and report the actual GB freed, plus a session total. Be honest: if something couldn't be removed (needed sudo, was in use), say so and explain the next step.

## What to NEVER delete without explicit, specific confirmation

These hold real data and must default to "review only":
- `~/Documents`, `~/Desktop`, `~/Pictures`, `~/Movies` actual files
- `.git` directories (project history)
- Outlook / Mail local databases (`~/Library/Group Containers/*Office/Outlook`, `~/Library/Mail`)
- Docker **volumes** (databases), and images the user says they still need
- Application data that isn't a cache (Notion/Slack/Chrome **profiles**, password stores, app databases)
- `~/Library/Application Support/<app>` beyond clearly-named cache subfolders
- Photos library, Music library, anything in iCloud Drive

When in doubt, show it under 🔴 and ask.
