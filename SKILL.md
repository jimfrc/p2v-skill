---
name: p2v-agent-skill
description: Generate a narrated short video (MP4) plus a per-scene slides PDF from a text prompt using the self-contained p2v-agent pipeline (AgentScope ReAct agent driving Remotion). Trigger when the user asks to generate, render, or build an explainer, promo, educational, or social-media video from a topic or script; to add voice-over narration, captions, or slides; or when they use Chinese terms such as 生成视频、做视频、讲解视频、宣传片、短视频、配音、幻灯片. Vendors the p2v-agent CLI, the prompt2video workflow, and 13 official Remotion skills, so it can be installed into any agent's skills folder.
license: MIT
---

# p2v-agent-skill

Turn a topic (or a short script) into:

- `out/video.mp4` — a rendered Remotion video with per-scene voice-over
- `out/slides.pdf` — one fully rendered still per scene
- `out/video.agent_events.jsonl` — the agent's event log (diagnostics)

The work is done by the vendored **p2v-agent** CLI: it scaffolds a blank
Remotion project, copies the bundled `prompt2video` + 13 official Remotion
skills into it, then runs an AgentScope `ReActAgent` that writes the scenes,
generates the narration, renders the video, and assembles the PDF.

This folder is self-contained. Nothing here is tied to the machine it was
packaged on.

## Requirements

- **Python ≥ 3.10** on `PATH` (`python3`/`python`, or `py -3` on Windows)
- **Node.js ≥ 20.12** with `npx` on `PATH`
- Network access on first use (PyPI for Python dependencies, npm for
  `create-video`/Remotion, and Remotion's browser if no local Chrome exists)
- An API key for a tool-calling model (DeepSeek by default; OpenAI, Anthropic,
  and DashScope are also supported)

Optional, platform-specific:

- macOS: built-in `say`; install `ffmpeg`/`ffprobe` for MP3 conversion
- Windows: PowerShell 5.1 `System.Speech` (built in; nothing to install)

## First-run setup

Set the model key in the **working directory** (not in this skill folder) via
`.env` or the environment. DeepSeek example:

```dotenv
P2V_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

`P2V_ENV_FILE=/path/to/.env` also works. Real environment variables always win.

Validate the machine without calling a model:

```bash
# macOS / Linux
bash <skill>/scripts/run.sh --check

# Windows (PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\run.ps1 --check
```

The first non-check run creates a cached virtualenv and installs the vendored
package. This can take several minutes. Later runs reuse it.

## Main workflow

1. **Write a prompt file** in the project/working directory. Use
   `key: value` control lines; every key is optional.

   ```text
   topic: Why the sky is blue
   description: |
     Explain Rayleigh scattering for curious adults in plain language.
   duration: 60s
   scenes: 4
   aspect: 16:9
   style: clean
   tone: casual
   audience: general
   language: English
   ```

   See `references/prompt-controls.md` for every key, the style presets, and
   duration budgeting.

2. **Run the pipeline.** Use a generous timeout (10–30 minutes is normal):

   ```bash
   bash <skill>/scripts/run.sh build \
     --prompt-file prompt.txt \
     --output-dir outputs \
     --tmp-dir /tmp/p2v-projects
   ```

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\run.ps1 build `
     --prompt-file prompt.txt `
     --output-dir outputs `
     --tmp-dir $env:TEMP
   ```

   `--dry-run` scaffolds the project and prints registered skills/tools without
   calling the model — useful for environment checks.

3. **Verify the deliverables** before reporting success:

   ```text
   outputs/p2v_agent_<timestamp>_video.mp4
   outputs/p2v_agent_<timestamp>_slides.pdf
   outputs/p2v_agent_<timestamp>_video.agent_events.jsonl
   ```

   Check both files exist and are non-trivial in size. If the CLI exits 0 but a
   file is missing, inspect the event log and see
   `references/troubleshooting.md`.

4. **Report** the absolute video and PDF paths, the duration/aspect used, and
   any warnings from the run.

## Prompt controls (short form)

| Key | Meaning | Default |
|---|---|---|
| `duration` | target length (`60s`, `90s`, `2m`) | 1–2 minutes |
| `scenes` | number of scenes / PDF pages | ~4–6 |
| `aspect` | `16:9`, `9:16`, `1:1` | `16:9` |
| `style` | `clean`, `dark`, `corporate`, `playful`, `cinematic`, or free-form | `clean` |
| `voice` | TTS voice name | system default |
| `rate` | narration words per minute | `175` |
| `tone` | narration register (`casual`, `formal`, …) | neutral |
| `audience` | reading level (`kids`, `experts`, …) | general |
| `language` | narration + on-screen language | English |
| `captions` | burn subtitles on screen (`on`/`off`) | `off` |
| `music` | background-music mood, or `off` | `off` |

## Alternative: use the bundled skills directly

If the host agent is already good at writing code and you do **not** want the
full pipeline, read and follow the vendored skills yourself:

- `vendor/p2v-agent/skills/prompt2video/SKILL.md` — end-to-end narrated video
  workflow (scenes, voice-over timing, render, slides PDF)
- `vendor/p2v-agent/skills/remotion-*/SKILL.md` — 13 official Remotion skills
  (create, markup, render, captions, maps, studio, docs, …)

This path skips p2v-agent's own model calls, but you still need Node/Remotion
and the TTS/PDF tools described in the `prompt2video` skill.

## References

| File | Contents |
|---|---|
| `references/quickstart.md` | Prerequisites, bootstrap, commands, outputs |
| `references/cli.md` | Full `p2v-agent` CLI reference |
| `references/configuration.md` | Providers, env vars, `.env` precedence, browser |
| `references/prompt-controls.md` | All controls, aspect sizes, style presets, duration math |
| `references/architecture.md` | Pipeline, agent loop, tool set, artifacts |
| `references/bundled-skills.md` | What each of the 14 bundled skills covers |
| `references/troubleshooting.md` | Network, Chromium, TTS, PDF, API, Windows issues |

## Scripts and assets

| Path | Purpose |
|---|---|
| `scripts/run.sh` | POSIX launcher (bootstraps the venv, forwards args) |
| `scripts/run.ps1` | Windows PowerShell launcher |
| `scripts/p2v.py` | Cross-platform bootstrap + CLI forwarder (`--check`, `--bootstrap-only`) |
| `assets/prompt.example.txt` | Starter prompt with common controls |
| `assets/prompts/` | Example prompts: explainer, vertical short, Chinese explainer |
| `assets/.env.example` | Environment template — copy to the working directory |
| `vendor/p2v-agent/` | Full p2v-agent source + 14 bundled skills |

## Notes and limits

- The first bootstrap installs Python dependencies into a cache directory
  (`%LOCALAPPDATA%\p2v-agent-skill` on Windows, `~/.cache/p2v-agent-skill`
  elsewhere). Override with `P2V_SKILL_VENV` or `P2V_SKILL_HOME`.
- The launcher runs from a cached copy of `vendor/`, so the skill folder can be
  moved or read-only. If the vendored files change, the cached copy and
  editable install refresh automatically on the next run.
- Models must support tool calling. DeepSeek defaults to non-streaming because
  of an AgentScope 1.0.21 streaming parser bug; use `P2V_STREAM=1` to opt in.
- The pipeline is autonomous: it will not ask the end user questions mid-run.
  Put every requirement (length, aspect, language, tone) in the prompt file.
