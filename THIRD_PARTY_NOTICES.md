# Third-party notices

## p2v-agent

- Source: this package's `vendor/p2v-agent/` (project: p2v-agent 0.1.0)
- License: MIT — see `vendor/p2v-agent/LICENSE`
- Copyright (c) 2026 Jerome Etienne

## prompt2video skill

- Vendored at `vendor/p2v-agent/skills/prompt2video/`
- Originates from the [prompt2video](https://github.com/jeromeetienne/prompt2video)
  project (MIT, see `vendor/p2v-agent/LICENSE`)
- Includes helper scripts: `tts.ps1`, `wav-duration.mjs`, `images-to-pdf.mjs`

## Remotion skills

- Vendored at `vendor/p2v-agent/skills/remotion-*` (13 skills)
- Source: [remotion-dev/skills](https://github.com/remotion-dev/skills),
  version `4.0.540`
- Consult the upstream repository for the license governing those skill files.
  The Remotion framework itself has its own license:
  <https://www.remotion.dev/docs/license>

## Runtime dependencies

The vendored project installs its Python dependencies from PyPI on first run
(`agentscope`, `mcp`, `tqdm`, `python-dotenv`). Generated Remotion projects
install npm packages (`remotion`, `@remotion/cli`, `pdf-lib`, …) under their
own licenses.
