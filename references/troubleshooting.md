# Troubleshooting

Start with the event log — it names the model, the registered skills, every
agent message, and the final error:

```text
<output-dir>/p2v_agent_<timestamp>_video.agent_events.jsonl
```

Also keep the generated project around (`--project-dir` lets you reuse it) so
you can rerun individual commands.

## Bootstrap / environment

**`p2v-agent-skill requires Python >= 3.10`**
Install a newer Python. On Windows, `py -3` selects the latest Python 3.

**First run takes forever / pip fails**
The first run installs `agentscope`, `mcp`, `tqdm`, `python-dotenv` and their
dependencies from PyPI. Check network/proxy. Retry; pip resumes from its cache.
Set `PIP_INDEX_URL` for a mirror.

**The skill folder was moved or the vendored source changed**
The launcher runs from a cached source copy, so moving the folder is fine. A
content-hash change triggers a cache/editable-install refresh. To force a full
rebuild, delete the cache directory (default `%LOCALAPPDATA%\p2v-agent-skill`
or `~/.cache/p2v-agent-skill`) or set a fresh `P2V_SKILL_HOME`.

**Cannot delete/recreate the venv (Windows)**
Some process may still hold files (editor, antivirus). Close it or point
`P2V_SKILL_VENV` at a new path.

**`No module named p2v_agent`**
Run through `scripts/run.sh` / `scripts/run.ps1` (they set `PYTHONPATH`), or run
`python scripts/p2v.py --bootstrap-only` first. Do not invoke the vendored
package with a different Python interpreter.

## Node / npm / Remotion

**`npx create-video` fails or is very slow**
- Node.js ≥ 20.12 and `npx` must be on `PATH` (`node --version`).
- Check npm registry access/proxy. `npx` caches downloads; a retry is often faster.
- On restricted networks, configure an npm mirror.

**`skills add remotion-dev/skills` times out**
Normally not needed: the 13 skills are vendored and copied locally. This only
runs when the vendored folders are missing. Restore `vendor/p2v-agent/skills/`
or allow `github.com:443`.

**Remotion downloads Chrome Headless Shell slowly**
p2v-agent auto-writes a local Chrome/Edge path into `remotion.config.ts`. Force
a path yourself:

```dotenv
P2V_BROWSER_EXECUTABLE=C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
```

To deliberately let Remotion download its browser, set it to `off`.

**Render hangs or consumes all memory**
- Use `--max-iters` if the agent loops; inspect the last tool call in the log.
- Lower scene count / duration / resolution for constrained machines.
- Ensure the browser path is a real browser executable, not a stub.
- A normal 60–90 s render can take several minutes; do not impose a 60 s
  timeout.

**`npx remotion still/render` reports a browser error**
Remove the `setBrowserExecutable` line from `remotion.config.ts` (or set
`P2V_BROWSER_EXECUTABLE=off`) and retry so Remotion uses its own headless shell.

## Voice-over (TTS)

**Windows: no audio / `tts.ps1` fails**
- Run it with `powershell -NoProfile -ExecutionPolicy Bypass -File …`.
- List voices:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .claude\skills\prompt2video\scripts\tts.ps1 -ListVoices`
- Pick a voice matching `language`; if the requested voice is missing the skill
  falls back to the closest installed one.
- PowerShell 5.1 (Windows PowerShell) is required; `pwsh` 7 may not expose
  `System.Speech`.

**macOS: `say` or `ffmpeg` errors**
`say` is built in. Install `ffmpeg`/`ffprobe` (e.g. `brew install ffmpeg`) for
AIFF → MP3 conversion and duration measurement. Without ffmpeg, narration may
render but timing measurement fails.

**Narration does not match the requested duration**
The skill budgets words then verifies measured audio; large deviations mean TTS
rate/voice differ from the assumption. Set `rate` explicitly and re-run. Allow
±10%.

## Slides PDF

**`Cannot find module 'pdf-lib'`**
The generated project installs it on demand, but you can do it manually:

```bash
cd <project-dir> && npm install pdf-lib
```

**PDF missing but MP4 exists**
The PDF is assembled after rendering from one still per scene. Inspect
`out/scene*.png` and the `images-to-pdf.mjs` command in the log. On Windows the
bundled `scripts/images-to-pdf.mjs` is the only supported path (ImageMagick is
optional on macOS).

**Slides are faded/blank**
Still frames are captured at the last fully opaque frame before the fade-out.
If you edited scene durations, re-derive the capture frames from
`src/Composition.tsx` as described in `prompt2video/SKILL.md`.

## Model / API

**401 / no credentials**
Set the provider's key in env or the working directory's `.env`. Run
`--check` to see which key variables are visible. Anthropic accepts an API key
or `ANTHROPIC_AUTH_TOKEN`.

**Model does not support tool calling**
The agent loop requires tools. Choose a tool-calling model; `deepseek-chat`,
`gpt-4o`, `claude-sonnet-5-5`, and `qwen-max` work.

**DeepSeek streaming crash**
Expected with AgentScope 1.0.21 when streaming is enabled. Leave `P2V_STREAM`
unset (DeepSeek defaults to non-streaming) or set `P2V_STREAM=0`.

**Context length / rate limit errors**
Shorten `duration`, reduce `scenes`, raise `--max-tokens` if the model truncates,
and retry after the rate-limit window. Very long runs are expensive; budget
accordingly.

**Agent stops early without artifacts**
The event log's `run_end.reply` usually explains why. Common causes: a failed
`npx` command, missing audio tool, or the model hitting `--max-iters`. Fix the
cause and rerun with `--project-dir <that project>`.

## Windows specifics

- Prefer `--prompt-file` over piping stdin; it avoids console encoding issues
  (a UTF-8 BOM is stripped automatically).
- Run long commands on a single line; the tools use cmd.exe/PowerShell
  non-interactively.
- Never end a command with `more`, `less`, or another pager; it can block
  forever.
- Paths with spaces are fine when the skill runs commands itself; quote them in
  your own manual experiments.

## Exit 0 but files missing

`build` succeeds only when it copied at least one of `video.mp4` /
`slides.pdf`. If both are missing it exits 1. If you ran the CLI with a custom
`--output-dir`, look there — filenames are
`p2v_agent_<timestamp>_video.mp4` and `p2v_agent_<timestamp>_slides.pdf`.
