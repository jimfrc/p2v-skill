# p2v-agent-skill

A portable, self-contained agent skill that turns a prompt into a narrated
Remotion video (MP4) plus a per-scene slides PDF. It vendors the complete
[p2v-agent](vendor/p2v-agent/) project — CLI, Python source, tests, and the 14
bundled skills — plus a bootstrapping launcher, references, and example assets.

Nothing is hard-coded to the machine it was packaged on. Copy the folder into
any agent's skills directory and it works.

## Layout

```text
p2v-agent-skill/
├── SKILL.md                    # Skill entry point (front matter + workflow)
├── references/                 # Deep reference material
│   ├── quickstart.md
│   ├── cli.md
│   ├── configuration.md
│   ├── prompt-controls.md
│   ├── architecture.md
│   ├── bundled-skills.md
│   └── troubleshooting.md
├── scripts/
│   ├── run.sh                  # POSIX launcher
│   ├── run.ps1                 # Windows PowerShell launcher
│   └── p2v.py                  # Bootstrap + CLI forwarder (--check, --bootstrap-only)
├── assets/
│   ├── .env.example
│   ├── prompt.example.txt
│   └── prompts/                # explainer-en, vertical-short-en, chinese-explainer
├── agents/
│   └── openai.yaml             # Optional UI metadata for OpenAI-style skill hosts
├── vendor/p2v-agent/           # Full p2v-agent 0.1.0 source + bundled skills
└── THIRD_PARTY_NOTICES.md
```

## Install into another agent

### Claude Code / AgentScope-style skills

Copy this directory into the host's skills folder:

```bash
# User-level Claude Code skills
cp -r p2v-agent-skill ~/.claude/skills/p2v-agent-skill

# Or project-level
cp -r p2v-agent-skill <project>/.claude/skills/p2v-agent-skill
```

The directory name matches the `name` in `SKILL.md` (`p2v-agent-skill`).
AgentScope can also register it directly with
`Toolkit.register_agent_skill("/abs/path/p2v-agent-skill")`.

### Bundled skills only

If the host only wants the inner skill content (no Python wrapper), copy the
vendored skills instead:

```bash
python p2v-agent-skill/scripts/p2v.py install ~/.claude
# -> ~/.claude/skills/prompt2video + 13 remotion-* skills
```

## Verify

```bash
bash scripts/run.sh --check
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run.ps1 --check
```

## Requirements

Python ≥ 3.10, Node.js ≥ 20.12 (`npx`), network on first bootstrap, and a
tool-calling model API key. DeepSeek is the default provider. See `SKILL.md`
and `references/configuration.md`.

## Updating the vendored project

Re-copy the source (excluding `.venv`, `.env`, `outputs`, caches) into
`vendor/p2v-agent/`. The launcher hashes the vendored files at startup and
refreshes its cached copy and editable install when the hash changes. The
skill folder itself is never written to at runtime.

## License

The vendored p2v-agent project and the `prompt2video` skill are MIT (see
`vendor/p2v-agent/LICENSE`). The 13 Remotion skills are vendored from
`remotion-dev/skills`; see `THIRD_PARTY_NOTICES.md` and the upstream repository
for their terms.
