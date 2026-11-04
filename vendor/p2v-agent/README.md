# p2v-agent

**用 AgentScope 替代 Claude Code 的 prompt2video，默认接入 DeepSeek API。** 给一句话（或一个 prompt 文件），它会：

1. 用 `npx create-video` 创建一个空白 Remotion 工程；
2. 把本工程自带的 Remotion 官方 13 个技能（`skills/remotion-*`，vendored 自 `remotion-dev/skills`）复制到工程的 `.claude/skills/`；本地副本缺失时回退到 `npx skills add remotion-dev/skills -a claude-code`；
3. 把本工程自带的 `skills/prompt2video/` 复制到工程的 `.claude/skills/prompt2video/`；
4. 启动一个基于 **AgentScope `ReActAgent`** 的编码智能体，让它读取技能、写 Remotion 代码、生成配音、渲染视频；
5. 把 `out/video.mp4`、`out/slides.pdf` 和智能体事件日志复制到输出目录。

> 本项目是 [`prompt2video`](https://github.com/jeromeetienne/prompt2video) 的重构版：原来的 `claude -p` 子进程被替换为 AgentScope 智能体，其余产物与工作流保持一致。

---

## 与 Claude Code 的对应关系

| 原 prompt2video | p2v-agent |
|---|---|
| `claude -p` 子进程 | AgentScope `ReActAgent`（Python） |
| Claude Code 内置工具 | 自定义工具：`Bash` / `Read` / `Write` / `Edit` / `Glob` / `Grep` / `WebFetch` |
| `.claude/skills` 自动加载 | `Toolkit.register_agent_skill()` 注册，System Prompt 自动注入技能描述 |
| `claude_stream_viewer` 流式展示 | AgentScope 内置流式打印 + JSONL 事件日志 |
| `video.claude_events.jsonl` | `video.agent_events.jsonl` |

工具名称刻意与 Claude Code 保持一致，因为技能文档里会直接写 “Use the Write tool” 等指令。

---

## 目录结构

```
p2v-agent/
├── pyproject.toml
├── README.md
├── .env                          # 本地密钥配置（gitignored）
├── .env.example                  # 环境变量模板
├── skills/                       # 自带技能（运行时会复制到生成的工程）
│   ├── prompt2video/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── images-to-pdf.mjs
│   │       ├── tts.ps1
│   │       └── wav-duration.mjs
│   └── remotion-*/               # 13 个 Remotion 官方技能（vendored）
│       └── SKILL.md
├── src/p2v_agent/
│   ├── cli.py                    # 命令行入口
│   ├── build.py                  # 创建工程 / 安装技能 / 跑智能体 / 拷贝产物
│   ├── agent_runner.py           # 构建并运行 AgentScope ReActAgent
│   ├── model_factory.py          # 默认 DeepSeek；可选 OpenAI / Anthropic / DashScope
│   ├── env.py                    # .env 环境变量加载
│   ├── tools.py                  # Bash / Read / Write / Edit / Glob / Grep / WebFetch
│   ├── skills.py                 # 技能发现、注册、安装
│   ├── prompts.py                # System Prompt 与用户提示包装
│   └── paths.py                  # 自带技能目录定位
└── tests/
```

---

## 环境要求

- **Python ≥ 3.10**
- **Node.js ≥ 20.12**（需要 `npx`；用于 `create-video`、`skills` CLI、Remotion）
- 一个支持 **tool calling** 的模型 API Key（见下文）
- 平台相关的 TTS / PDF 依赖与原项目相同：
  - macOS：内置 `say`；建议安装 `ffmpeg`/`ffprobe`
  - Windows：内置 PowerShell 5.1 `System.Speech`，无需额外安装

---

## 安装

```powershell
cd <p2v-agent-skill>\vendor\p2v-agent

# 建议使用虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装（会安装 agentscope 及其依赖）
pip install -e .

# 验证
p2v-agent --version
```

> agentscope 依赖较多（openai、anthropic、dashscope、numpy、tiktoken 等），首次安装需要几分钟。

---

## 快速开始

先配置 DeepSeek API Key（`.env` 会被自动加载）：

```powershell
cd <p2v-agent-skill>\vendor\p2v-agent

# 首次使用：从模板创建 .env，并填入你的 DeepSeek Key
Copy-Item .env.example .env

# 或者直接写环境变量（优先级高于 .env）
$env:DEEPSEEK_API_KEY = "sk-..."
```

`.env` 示例：

```dotenv
P2V_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Windows（推荐用 `--prompt-file`，避免控制台编码问题）：

```powershell
cd <p2v-agent-skill>\vendor\p2v-agent
p2v-agent build --prompt-file prompt.example.txt
```

macOS / Linux：

```bash
echo "用 10 岁小朋友能懂的方式讲讲量子物理" \
  | p2v-agent build
```

产物默认输出到 `./outputs/`：

```
outputs/p2v_agent_<timestamp>_video.mp4
outputs/p2v_agent_<timestamp>_slides.pdf
outputs/p2v_agent_<timestamp>_video.agent_events.jsonl
```

生成的 Remotion 工程位于系统临时目录：`%TEMP%\p2v_agent_<timestamp>`（可用 `--tmp-dir` 指定父目录）。

### 只做脚手架和技能安装（不调用模型）

```powershell
p2v-agent build --dry-run --prompt-file prompt.example.txt
```

它会创建工程、安装 Remotion 技能、复制 `prompt2video` 技能，并打印注册到的技能与工具列表，然后退出。适合验证环境。

### 复用已有工程

```powershell
p2v-agent build --project-dir D:\temp\p2v_agent_2026-11-03T12-00-00-000Z --prompt-file prompt.example.txt
```

---

## 模型配置（默认 DeepSeek）

p2v-agent 默认调用 **DeepSeek 官方 API**（`https://api.deepseek.com`，OpenAI 兼容协议），默认模型 `deepseek-chat`。

### 环境变量加载顺序

1. 真实进程环境变量（优先级最高）
2. `P2V_ENV_FILE` 指定的文件
3. 从当前目录向上查找的 `.env`
4. 工程根目录的 `.env`

`.env` 不会覆盖已经存在的环境变量，适合把密钥放在本地文件里。

### 自动检测顺序

1. `P2V_PROVIDER`
2. `DEEPSEEK_API_KEY` 或 `P2V_API_KEY` → `deepseek`（默认）
3. `DASHSCOPE_API_KEY` → `dashscope`
4. `ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN` → `anthropic`
5. `OPENAI_API_KEY` → `openai`

### 各后端变量

| Provider | 必填 | 可选 | 默认模型 |
|---|---|---|---|
| `deepseek`（默认） | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `OPENAI_BASE_URL`、`OPENAI_MODEL` | `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN` | `ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL` | `claude-sonnet-5-5` |
| `dashscope` | `DASHSCOPE_API_KEY` | `DASHSCOPE_MODEL` | `qwen-max` |

通用变量（优先级更高）：`P2V_PROVIDER`、`P2V_MODEL`、`P2V_BASE_URL`、`P2V_API_KEY`、`P2V_AUTH_TOKEN`、`P2V_STREAM`。

### 示例

**DeepSeek（默认，无需 `--provider`）**

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
p2v-agent build --prompt-file prompt.example.txt
```

也可以指定 reasoning 模型：

```powershell
p2v-agent build --prompt-file prompt.example.txt --model deepseek-reasoner
```

**DashScope / Qwen**

```powershell
$env:DASHSCOPE_API_KEY = "sk-..."
p2v-agent build --prompt-file prompt.example.txt --provider dashscope --model qwen-max
```

**Anthropic 兼容代理**

```powershell
p2v-agent build --prompt-file prompt.example.txt --provider anthropic
```

**OpenAI 兼容的第三方端点**

```powershell
p2v-agent build --prompt-file prompt.example.txt `
  --provider openai --model your-model `
  --base-url https://your-endpoint/v1 --api-key sk-...
```

> 为了安全，优先使用环境变量或 `.env`，不要用 `--api-key`；日志里只会显示 `api_key=***`。
>
> **流式输出**：AgentScope 1.0.21 的 OpenAI 流式解析器在遇到 DeepSeek 返回的 `"audio": null` 时会崩溃，因此 DeepSeek 默认使用非流式模式（工具调用和智能体循环不受影响）。如需尝试流式，可设置 `P2V_STREAM=1` 或 `--stream`。

---

## Prompt controls

和原项目一致，prompt 可以使用可选的 `key: value` 控制行；省略时使用默认值。

| Key | 作用 | 示例 | 默认 |
|---|---|---|---|
| `duration` | 目标总时长 | `90s`、`2m` | 1–2 分钟 |
| `scenes` | 场景 / 幻灯片数量 | `5` | ~4–6 |
| `aspect` | 画幅 | `16:9`、`9:16`、`1:1` | `16:9` |
| `style` | 视觉风格预设或描述 | `dark, neon accents` | `clean` |
| `voice` | TTS 音色 | `Samantha`、`Microsoft Huihui Desktop` | 系统默认 |
| `rate` | 语速（词/分钟） | `160` | 175 |
| `tone` | 叙述语气 | `casual`、`formal` | 中性 |
| `audience` | 目标受众 | `kids`、`experts` | 普通 |
| `language` | 旁白与画面语言 | `Chinese` | English |
| `captions` | 是否烧录字幕 | `on`、`off` | `off` |
| `music` | 背景音乐氛围或 `off` | `upbeat`、`off` | `off` |

内置 `style` 预设：`clean`、`dark`、`corporate`、`playful`、`cinematic`。

---

## 技能机制（重点）

工程里自带了 14 个技能，运行时全部复制到 `<工程>/.claude/skills/`：

| 技能 | 来源 | 说明 |
|---|---|---|
| `prompt2video` | 本仓库 `skills/prompt2video/` | 视频生成主流程：配音、分镜、时长控制、PDF 幻灯片 |
| `remotion-*`（13 个） | vendored 自 [`remotion-dev/skills`](https://github.com/remotion-dev/skills) v4.0.540 | Remotion 官方技能：`best-practices`、`create`、`markup`、`render`、`captions`、`maps`、`studio`、`docs` 等 |

复制逻辑：

1. `skills/remotion-*` 存在时直接本地复制（无需网络，版本可复现）；
2. 本地副本缺失（例如旧版 wheel 安装）时，回退执行：

   ```text
   npx skills add remotion-dev/skills -a claude-code --yes --copy
   ```

   `--copy` 避免 Windows 上创建符号链接需要管理员权限；`-a claude-code` 使用 Claude Code 的技能目录布局，AgentScope 直接读取同一批文件。

`prompt2video` 技能保留原位置，其相对路径（`scripts/tts.ps1` 等）在生成的工程里可直接执行。

随后 p2v-agent 用 `agentscope.tool.Toolkit.register_agent_skill()` 逐个注册这些目录。AgentScope 会把每个技能的 `name` / `description` 注入 System Prompt，智能体再通过 `Read` 工具读取 `SKILL.md` 获取详细步骤。

---

## 网络受限：跳过 Chrome Headless Shell 下载

Remotion 首次渲染会下载约 130 MB 的 Chrome Headless Shell。在国内或受限网络中可能非常慢（实测 15 分钟只下载了 9 MB），导致 `npx remotion still/render` 长时间卡住。

p2v-agent 会在脚手架完成后自动查找本机 Chromium 浏览器，并写入生成的 `remotion.config.ts`：

```ts
Config.setBrowserExecutable("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe");
```

查找顺序：

1. `P2V_BROWSER_EXECUTABLE` / `REMOTION_BROWSER_EXECUTABLE`
2. Windows：Chrome、Edge 常见安装路径
3. macOS：Chrome、Edge、Chromium
4. Linux：`google-chrome`、`chromium`、`microsoft-edge` 等

强制让 Remotion 自己下载（不推荐在慢网络下使用）：

```powershell
$env:P2V_BROWSER_EXECUTABLE = "off"
```

`.env` 中也可以设置：

```dotenv
P2V_BROWSER_EXECUTABLE=C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
```

---

## CLI

```text
p2v-agent [--version] {build,install} ...

build:
  -t, --tmp-dir <dir>       生成工程的父目录（默认：系统临时目录）
  -o, --output-dir <dir>    产物输出目录（默认：./outputs）
  -f, --prompt-file <file>  从 UTF-8 文件读取 prompt
      --project-dir <dir>   复用已有 Remotion 工程
      --dry-run             只脚手架 + 安装技能，不调用模型
      --provider <name>     deepseek（默认）| openai | anthropic | dashscope
      --model <name>        模型名（默认 deepseek-chat）
      --base-url <url>      OpenAI/Anthropic 兼容端点
      --api-key <key>       API Key（建议改用环境变量或 .env）
      --max-tokens <n>      单次模型输出的最大 token 数（默认 8192）
      --max-iters <n>       智能体最大推理/行动轮数（默认 200）
      --stream / --no-stream  流式输出开关（DeepSeek 默认关闭）

install [agents-folder]:
  把自带技能复制到 <agents-folder>/skills/
```

### 单独安装自带技能

```powershell
p2v-agent install ~/.claude
# -> <agents-folder>/skills/prompt2video
# -> <agents-folder>/skills/remotion-*   （13 个 Remotion 官方技能）
```

---

## 测试

```powershell
pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

测试覆盖：工具读写 / 编辑 / 搜索 / shell、技能发现与注册、模型配置解析、`.env` 加载、prompt 读取。

---

## 工作原理与限制

- **智能体拥有真实 shell 权限**：`Bash` 工具会在生成工程目录中执行任意命令，和 Claude Code 的 `--permission-mode auto` 等价。只在你信任的 prompt 上运行。
- **模型必须支持 tool calling**：AgentScope 通过 OpenAI/Anthropic 的 tool use 接口驱动工具。纯文本模型无法完成任务。DeepSeek 的 `deepseek-chat` / `deepseek-reasoner` 均支持。
- **DeepSeek 默认非流式**：受 AgentScope 1.0.21 流式解析 bug 影响，DeepSeek 使用非流式请求；智能体的工具调用与事件日志不受影响。可用 `P2V_STREAM=1` 强制开启。
- **密钥安全**：`.env` 已在 `.gitignore` 中；日志只显示 `api_key=***`。不要把真实密钥提交到版本库。
- **渲染耗时**：Remotion 首次渲染会下载 Chromium/ffmpeg，`npx remotion render` 可能需要几分钟到十几分钟；`Bash` 默认超时 600 秒，智能体可以为长时间命令调高到 3600 秒。
- **Windows 编码**：`Bash` 工具会按 UTF-8 → 系统代码页 → GBK 的顺序解码输出，避免中文输出导致工具崩溃。
- **输出路径被显式固定**：用户提示中要求智能体把视频写到 `out/video.mp4`、PDF 写到 `out/slides.pdf`，确保编排层能稳定拷贝。

---

## License

MIT © Jerome Etienne（原始 prompt2video 作者）与 p2v-agent contributors。
