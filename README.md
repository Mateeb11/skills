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

## Install

Using the [skills CLI](https://skills.sh):

```bash
npx skills add Mateeb11/skills@screenshot-markup
```

Or symlink directly into your Claude config:

```bash
git clone https://github.com/Mateeb11/skills.git ~/code/Mateeb11-skills
ln -s ~/code/Mateeb11-skills/skills/screenshot-markup ~/.claude/skills/screenshot-markup
```

## License

[MIT](./LICENSE)
