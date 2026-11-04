# Bundled skills

All 14 live under `vendor/p2v-agent/skills/`. During `build`, they are copied
into the generated Remotion project's `.claude/skills/`. They can also be read
directly by a host agent that wants to do the work itself.

| Skill | What it covers |
|---|---|
| `prompt2video` | **Primary workflow.** Prompt controls, per-scene narration, measured audio → frame durations, rendering, one-still-per-scene PDF. Read this first. |
| `remotion-best-practices` | Router for the Remotion skill set; preserve-user-changes rule. |
| `remotion-create` | Scaffold a Remotion project/composition; Tailwind; video layout. |
| `remotion-markup` | Deep reference: compositions, sequencing, timing, transitions, text, audio, images, video, fonts, effects, 3D, Lottie, measuring, voice-over, SFX. |
| `remotion-render` | Export strategy, transparent videos, browser selection. |
| `remotion-captions` | Caption data model, SRT import, transcription, animated/displayed captions. |
| `remotion-maps` | Map animations: static maps, Mapbox, MapLibre, MapTiler, Cesium 3D flyovers. |
| `remotion-multimedia` | Mediabunny: audio/video duration, video dimensions. |
| `remotion-studio` | Preview the composition in Remotion Studio. |
| `remotion-docs` | Search the live Remotion documentation (Algolia API). |
| `remotion-interactivity` | Structure markup so Studio timeline items stay editable. |
| `remotion-saas` | Build apps/players/rendering services with Remotion. |
| `remotion-upgrade` | Upgrade Remotion and related packages safely. |
| `remotion-license` | License, FAQ, and where to buy a Remotion license. |

## Source and version

Vendored from [`remotion-dev/skills`](https://github.com/remotion-dev/skills),
version `4.0.540` per each `SKILL.md` front matter. Refresh with:

```bash
npx --yes skills add remotion-dev/skills -a claude-code --yes --copy
```

Then replace `vendor/p2v-agent/skills/remotion-*` with the generated folders.

## Which to read

- Generating the deliverable video → `prompt2video` first, then
  `remotion-markup` / `remotion-render` for specific techniques.
- Debugging a render or a Remotion API → `remotion-render`,
  `remotion-best-practices`, then `remotion-docs`.
- Captions, maps, studio, upgrades → the matching `remotion-*` skill.
- License questions → `remotion-license`.
