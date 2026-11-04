# Architecture

## What runs

```
prompt file
   │
   ▼
p2v-agent CLI  ──► scaffold Remotion project (npx create-video)
   │                 install 13 Remotion skills + prompt2video skill
   │                 configure local browser in remotion.config.ts
   ▼
AgentScope ReActAgent (DeepSeek/OpenAI/Anthropic/DashScope)
   │  tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
   │  loop: read SKILL.md → write scenes → TTS → render → PDF
   ▼
out/video.mp4 + out/slides.pdf + event log
   │
   ▼
<output-dir>/p2v_agent_<timestamp>_*
```

## Components

| File | Responsibility |
|---|---|
| `src/p2v_agent/cli.py` | Argument parsing and command dispatch |
| `src/p2v_agent/build.py` | Scaffold, skill install, browser config, agent run, artifact copy |
| `src/p2v_agent/agent_runner.py` | Build/run the `ReActAgent`, JSONL event logging |
| `src/p2v_agent/model_factory.py` | Provider selection and model/formatter construction |
| `src/p2v_agent/tools.py` | Claude-Code-like tool implementations |
| `src/p2v_agent/skills.py` | Skill discovery, registration, copying |
| `src/p2v_agent/paths.py` | Bundled-skill resolution |
| `src/p2v_agent/prompts.py` | System prompt and prompt wrapping |
| `src/p2v_agent/env.py` | `.env` loading |
| `src/p2v_agent/browser.py` | Local Chromium detection for Remotion |

## Skill registration

AgentScope implements Anthropic-style skills: a directory with `SKILL.md`
whose front matter declares `name` and `description`.

1. `discover_skill_dirs()` finds `SKILL.md` one level below each root.
2. `register_skills()` calls `Toolkit.register_agent_skill()` for each.
3. AgentScope injects each skill's name/description into the system prompt.
4. The agent reads the full `SKILL.md` on demand with the `Read` tool.

Roots: `<project>/.claude/skills`, `<project>/skills`, plus
`P2V_EXTRA_SKILLS_DIRS`.

## Skills: local first

`build` copies the vendored `skills/remotion-*` folders into the generated
project. Only if they are absent does it call
`npx skills add remotion-dev/skills -a claude-code --yes --copy`. This makes
builds deterministic and offline-capable for the skill-install step (npm and
Remotion still need network on first use).

`prompt2video` is always copied from `skills/prompt2video/`, preserving its
`scripts/` relative paths so `tts.ps1`, `wav-duration.mjs`, and
`images-to-pdf.mjs` work in the generated project.

## Agent behavior rules

The system prompt instructs the agent to:

- Work autonomously, end to end, without asking questions.
- Follow `prompt2video` in order; it overrides Remotion's "preview only" advice.
- Treat `out/video.mp4` and `out/slides.pdf` as required deliverables.
- Keep scene durations in sync with measured audio.
- Never start a blocking dev server or pager.
- Verify by command exit codes and file existence (the model may be text-only).

The user prompt is wrapped with explicit deliverable paths before the run, so
the orchestrator can find the artifacts reliably.

## Event log

`out/video.agent_events.jsonl` (copied as
`p2v_agent_<timestamp>_video.agent_events.jsonl`) contains:

- a `run_start` record with project dir, model summary, registered skill names,
  and the wrapped prompt
- one `message` record per finalized agent message
- a `run_end` record with elapsed time and the final reply

Use it to diagnose why a render failed or which skill was loaded.

## Artifacts and project layout

```text
<tmp-dir>/p2v_agent_<timestamp>/
├── .claude/skills/
│   ├── prompt2video/
│   └── remotion-*/
├── public/scenes/       # narration .txt + .wav/.mp3
├── src/                 # Remotion components and composition
├── out/
│   ├── video.mp4
│   ├── slides.pdf
│   ├── scene1.png …
│   └── video.agent_events.jsonl
└── remotion.config.ts
```

## Models

Any tool-calling model supported by AgentScope works. Defaults: `deepseek-chat`
(DeepSeek), `gpt-4o` (OpenAI), `claude-sonnet-5-5` (Anthropic), `qwen-max`
(DashScope). See `configuration.md`.
