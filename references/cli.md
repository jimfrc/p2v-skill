# CLI reference

The vendored project exposes the `p2v-agent` command. This skill's launcher
(`scripts/run.sh`, `scripts/run.ps1`) bootstraps the venv and forwards every
argument to that CLI, so either form works:

```bash
python scripts/p2v.py build --prompt-file prompt.txt
bash scripts/run.sh build --prompt-file prompt.txt
```

```text
p2v-agent [--version] {build,install} ...
```

## `build`

Scaffold a Remotion project, install skills, run the agent, copy artifacts.

| Flag | Meaning | Default |
|---|---|---|
| `-t, --tmp-dir <dir>` | Parent directory for the generated project | OS temp dir |
| `-o, --output-dir <dir>` | Where video/PDF/event log are copied | `./outputs` |
| `-f, --prompt-file <file>` | Read the prompt from a UTF-8 file (BOM stripped) | stdin |
| `--project-dir <dir>` | Reuse an existing Remotion project instead of scaffolding | none |
| `--dry-run` | Scaffold + install skills, print skills/tools, do not call the model | off |
| `--provider <name>` | `deepseek` (default), `openai`, `anthropic`, `dashscope` | auto-detect |
| `--model <name>` | Model name; overrides `P2V_MODEL` | provider default |
| `--base-url <url>` | OpenAI/Anthropic-compatible endpoint | provider default |
| `--api-key <key>` | API key (prefer env/.env; logs show `api_key=***`) | env |
| `--max-tokens <n>` | Max output tokens per model call | `8192` |
| `--max-iters <n>` | Max agent reasoning/action iterations | `200` |
| `--stream / --no-stream` | Streaming output | off for DeepSeek, on otherwise |

### Pipeline

1. Resolve model credentials **before** scaffolding (fail fast).
2. `npx --yes create-video@latest --yes --blank <project>` in `<tmp-dir>`.
3. Copy the 13 bundled `remotion-*` skills into
   `<project>/.claude/skills/` (local first; fall back to
   `npx skills add remotion-dev/skills -a claude-code --yes --copy`).
4. Copy `skills/prompt2video/` to `<project>/.claude/skills/prompt2video/`.
5. Detect a local Chrome/Edge and write `Config.setBrowserExecutable(...)` into
   `remotion.config.ts`.
6. Run the AgentScope `ReActAgent` with the wrapped prompt and JSONL event log.
7. Copy artifacts into `--output-dir`.

### Outputs

```text
<output-dir>/p2v_agent_<timestamp>_video.mp4
<output-dir>/p2v_agent_<timestamp>_slides.pdf
<output-dir>/p2v_agent_<timestamp>_video.agent_events.jsonl
```

`build` fails (exit 1) if the agent finishes without either `video.mp4` or
`slides.pdf`. The event log path is printed on failure.

### Examples

```bash
# Default DeepSeek, prompt from a file
bash scripts/run.sh build -f prompt.txt

# stdin prompt (macOS/Linux)
echo "Explain quantum physics for a 10-year-old" | bash scripts/run.sh build

# Reuse an existing project (skills and browser config are refreshed; no scaffold)
bash scripts/run.sh build --project-dir /tmp/p2v_agent_2026-11-03T12-00-00-000Z -f prompt.txt

# Environment check without an LLM
bash scripts/run.sh build --dry-run -f prompt.txt
```

`--project-dir` reuses the project directory but still refreshes the skills and
browser config.

## `install [agents-folder]`

Copy every bundled skill directory (`prompt2video` + 13 `remotion-*`) into
`<agents-folder>/skills/`. Useful for enriching another agent:

```bash
bash scripts/run.sh install ~/.claude
# -> ~/.claude/skills/prompt2video
# -> ~/.claude/skills/remotion-*
```

The destination default is the current directory (`.`).

## Wrapper-only options

| Option | Effect |
|---|---|
| `--check` | Validate prerequisites without installing or calling a model |
| `--bootstrap-only` | Create/repair the venv and print its Python path |
| `--cli-help` | Show the forwarded `p2v-agent --help` |
| `-h, --help` | Show the launcher help |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Configuration/build error (missing key, failed command, missing artifact) |
| `130` | Interrupted (Ctrl+C) |

## Tool set available to the agent

`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch` — deliberately named
like Claude Code's tools because the bundled skill docs refer to them by name.
