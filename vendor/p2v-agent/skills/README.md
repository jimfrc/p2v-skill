# Bundled skills

| Skill | Source |
|---|---|
| `prompt2video` | Bundled with p2v-agent (see `../README.md`). |
| `remotion-*` (13 skills) | Vendored from [remotion-dev/skills](https://github.com/remotion-dev/skills), version `4.0.540` (per each `SKILL.md` front matter). See that repository for licenses and updates. |

`p2v-agent build` copies these into a generated project's
`.claude/skills/` (the `remotion-*` skills come from here first; if they are
missing, the build falls back to `npx skills add remotion-dev/skills`).

`p2v-agent install <folder>` copies every skill directory into
`<folder>/skills/`.

To refresh the vendored skills from upstream:

```powershell
npx --yes skills add remotion-dev/skills -a claude-code --yes --copy
```

Then copy the generated `.claude/skills/remotion-*` folders over the ones here.
