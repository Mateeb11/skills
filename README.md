# skills

A collection of [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) skills by [@Mateeb11](https://github.com/Mateeb11).

## Skills in this repo

### [screenshot-markup](./skills/screenshot-markup/)

Draw on, annotate, and mark up screenshots — circles, rectangles, arrows, spotlights, blur effects, macOS cursors, and zoomed insets. Designed to plug into the Playwright MCP screenshot workflow: browse → screenshot → "draw a circle on the Send button" → annotated PNG.

Four styles:

- **`spotlight`** — dim everything outside the focus area
- **`blur`** — soft-focus everything outside the focus area
- **`shape`** — Skitch-style circle/rectangle outline with optional arrow + caption
- **`cursor-zoom`** — macOS cursor overlay + magnified inset, with auto light/dark cursor selection

See [`skills/screenshot-markup/SKILL.md`](./skills/screenshot-markup/SKILL.md) for the full reference.

### [mac-disk-cleanup](./skills/mac-disk-cleanup/)

Scan a Mac for reclaimable disk space and let **you** decide what to delete. The scan is read-only; deletion is always interactive and confirmed. Surfaces only genuinely safe-to-remove things — caches, rebuildable artifacts, duplicates, and leftovers — never your real documents, code, photos, or app data.

What it looks for:

- **Caches** — system, app, and user caches that regenerate automatically
- **Package-manager caches** — npm, pnpm, gradle, uv, Homebrew
- **Dev artifacts** — `node_modules`, Python venvs, build output
- **Docker** — dangling images and build cache
- **iOS simulators** — old/unavailable runtimes and devices
- **Duplicates & leftovers** — duplicate editor extensions, old downloads, updater installers

Findings are grouped by size and safety before anything is removed. See [`skills/mac-disk-cleanup/SKILL.md`](./skills/mac-disk-cleanup/SKILL.md) for the full reference.

## Install

Using the [skills CLI](https://skills.sh):

```bash
# install everything in the repo
npx skills add Mateeb11/skills

# or a single skill
npx skills add Mateeb11/skills@screenshot-markup
npx skills add Mateeb11/skills@mac-disk-cleanup
```

Or symlink directly into your Claude config:

```bash
git clone https://github.com/Mateeb11/skills.git ~/code/Mateeb11-skills
ln -s ~/code/Mateeb11-skills/skills/screenshot-markup ~/.claude/skills/screenshot-markup
ln -s ~/code/Mateeb11-skills/skills/mac-disk-cleanup  ~/.claude/skills/mac-disk-cleanup
```

## License

[MIT](./LICENSE)
