# Quickstart

## 1. Check the machine

```bash
bash scripts/run.sh --check
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run.ps1 --check
```

This verifies Python ≥ 3.10, Node.js ≥ 20.12, `npx`, the vendored project, the
14 bundled skills, API-key environment variables, and a local Chromium browser.
It does **not** install anything or call a model.

## 2. Provide credentials

Create `.env` in the **working directory** where you run the command (not in
the skill folder):

```dotenv
P2V_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key
```

Or export variables in the shell. Real environment variables beat `.env`.
Supported providers and variables are listed in `configuration.md`.

## 3. Write a prompt

`assets/prompt.example.txt` is a working starting point:

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

Do not pass control lines as CLI flags; they belong in the prompt file and are
interpreted by the `prompt2video` skill. See `prompt-controls.md`.

## 4. Build

```bash
bash scripts/run.sh build \
  --prompt-file prompt.txt \
  --output-dir outputs \
  --tmp-dir /tmp/p2v-projects
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run.ps1 build `
  --prompt-file prompt.txt `
  --output-dir outputs `
  --tmp-dir $env:TEMP
```

The first run creates a cached virtualenv and installs the Python dependencies
(several minutes). The video render itself commonly takes 5–30 minutes. Use a
generous timeout when an agent invokes this.

## 5. Verify outputs

```text
outputs/p2v_agent_<timestamp>_video.mp4
outputs/p2v_agent_<timestamp>_slides.pdf
outputs/p2v_agent_<timestamp>_video.agent_events.jsonl
```

Both the MP4 and the PDF must exist and be non-empty. On success the CLI also
prints their paths.

## Environment-only check without a model

```bash
bash scripts/run.sh build --dry-run --prompt-file prompt.txt
```

This scaffolds a project, installs the skills, prints the registered skills and
tools, and exits without calling the model.

## Where things live

| Item | Location |
|---|---|
| Generated Remotion project | `<tmp-dir>/p2v_agent_<timestamp>` (`--project-dir` to reuse) |
| Cached venv | `%LOCALAPPDATA%\p2v-agent-skill\venv` (Windows), `~/.cache/p2v-agent-skill/venv` (Linux), `~/Library/Caches/p2v-agent-skill/venv` (macOS) |
| Cached source copy | Same cache root, under `vendor/p2v-agent` (the skill folder is never modified) |
| Cache overrides | `P2V_SKILL_HOME`, `P2V_SKILL_VENV`, `P2V_SKILL_VENDOR` |
| Bundled skills | `vendor/p2v-agent/skills/` |
| Full project docs | `vendor/p2v-agent/README.md` |

The launcher runs from its cached source copy, so moving the skill folder does
not invalidate the venv. If you edit the vendored files, the next run detects
the content-hash change and refreshes the cache and editable install.
