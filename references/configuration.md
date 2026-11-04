# Configuration

## `.env` loading order

1. Real process environment variables (always win)
2. File named by `P2V_ENV_FILE`
3. The nearest `.env` found from the current working directory upward
4. The cached project copy's `.env` (do not store secrets there)

Loads never override an already-set variable. Put `.env` in the directory where
you run the command, or point `P2V_ENV_FILE` at it.

## Provider detection

1. `P2V_PROVIDER` (explicit)
2. `DEEPSEEK_API_KEY` or `P2V_API_KEY` → `deepseek` (default)
3. `DASHSCOPE_API_KEY` → `dashscope`
4. `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` → `anthropic`
5. `OPENAI_API_KEY` → `openai`
6. Otherwise `deepseek`, which then reports a missing-key error

Provider aliases: `claude` → `anthropic`, `gpt` → `openai`, `qwen`/`aliyun` →
`dashscope`.

## Provider variables

| Provider | Required | Optional | Default model |
|---|---|---|---|
| `deepseek` (default) | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `OPENAI_BASE_URL`, `OPENAI_MODEL` | `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` | `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL` | `claude-sonnet-5-5` |
| `dashscope` | `DASHSCOPE_API_KEY` | `DASHSCOPE_MODEL` | `qwen-max` |

Generic overrides with higher priority: `P2V_PROVIDER`, `P2V_MODEL`,
`P2V_BASE_URL`, `P2V_API_KEY`, `P2V_AUTH_TOKEN`, `P2V_STREAM`.

For Anthropic, an explicit API key wins over `ANTHROPIC_AUTH_TOKEN`.

## Streaming

`P2V_STREAM=1/0` or `--stream/--no-stream`. Defaults: **off for DeepSeek**, on
for other providers. AgentScope 1.0.21's OpenAI streaming parser crashes on
DeepSeek's `"audio": null` delta; non-streaming is unaffected.

## Browser / Chrome Headless Shell

Remotion downloads ~130 MB Chrome Headless Shell on first render. p2v-agent
prefers a local browser and writes it into the generated `remotion.config.ts`.

- Override: `P2V_BROWSER_EXECUTABLE` (or `REMOTION_BROWSER_EXECUTABLE`)
- Disable detection and force Remotion's download: set it to `off`, `none`,
  `0`, or `false`
- Auto-detect order: Windows Chrome/Edge paths → macOS Chrome/Edge/Chromium →
  Linux `google-chrome`, `chromium`, `microsoft-edge`, …
- If the override path does not exist, a warning is printed and detection is
  skipped (Remotion downloads its own browser)

## Agent limits

| Setting | Source | Default |
|---|---|---|
| model | `--model`, `P2V_MODEL`, `<PROVIDER>_MODEL` | provider default |
| max output tokens | `--max-tokens` | 8192 |
| max agent iterations | `--max-iters` | 200 |

## Skill discovery

The agent registers skills from:

1. `<project>/.claude/skills`
2. `<project>/skills`
3. Extra roots in `P2V_EXTRA_SKILLS_DIRS` (split on the OS path separator)

Duplicate skill names are skipped. A malformed `SKILL.md` is ignored rather
than aborting the build.

## Launcher variables (this skill only)

| Variable | Effect |
|---|---|
| `P2V_SKILL_HOME` | Cache directory for the venv and cached source copy |
| `P2V_SKILL_VENV` | Exact venv path override |
| `P2V_SKILL_VENDOR` | Exact cached-source path override |
| `P2V_SKILL_ROOT` | Set automatically; points at the skill folder |

The launcher runs from a cached copy of `vendor/p2v-agent/`, never from the
skill folder itself, so the skill folder can be read-only. When the vendored
source changes (its content hash changes), the cached copy and editable install
are refreshed automatically.

## Template

`assets/.env.example`:

```dotenv
P2V_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
# P2V_BROWSER_EXECUTABLE=C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
# P2V_BROWSER_EXECUTABLE=off
```
