# Prompt controls

The prompt file is plain text. `topic:` / `description:` carry the content;
optional `key: value` lines steer the render. Every key is optional, and
free-text instructions ("make it about a minute, vertical, for kids") are
mapped to the same controls by the `prompt2video` skill.

| Key | Meaning | Example | Default |
|---|---|---|---|
| `duration` | target total length | `60s`, `90s`, `2m` | 1–2 minutes |
| `scenes` | number of scenes / PDF pages | `5` | ~4–6 |
| `aspect` | frame shape | `16:9`, `9:16`, `1:1` | `16:9` |
| `style` | preset and/or free-form descriptors | `dark, neon accents` | `clean` |
| `voice` | TTS voice | `Samantha`, `Microsoft Huihui Desktop` | system default |
| `rate` | narration words per minute | `160` | `175` |
| `tone` | narration register | `casual`, `formal`, `enthusiastic` | neutral |
| `audience` | reading level / audience | `kids`, `experts` | general |
| `language` | narration + on-screen language | `Chinese` | English |
| `captions` | burn subtitles on screen | `on`, `off` | `off` |
| `music` | background-music mood, or `off` | `upbeat`, `off` | `off` |

## Aspect → composition size

| `aspect` | width × height |
|---|---|
| `16:9` (default) | 1920 × 1080 |
| `9:16` | 1080 × 1920 |
| `1:1` | 1080 × 1080 |

## Style presets

| Preset | Look |
|---|---|
| `clean` (default) | White/light background, near-black text, one blue accent, system sans |
| `dark` | Near-black/deep navy, off-white text, neon-cyan accent, soft glow |
| `corporate` | White with rule lines, navy + slate, serif headings |
| `playful` | Warm pastel, bold high-contrast colors, rounded shapes, springy motion |
| `cinematic` | Black with letterbox bars, white serif, gold accent, slow ken-burns |

Free-form descriptors override individual preset tokens.

## Duration budgeting

Total length follows the measured voice-over, not a hard cut. At `rate` wpm:

- 60 s @ 175 wpm → ~175 words across all scenes
- 90 s @ 175 wpm → ~260 words
- 120 s @ 175 wpm → ~350 words

After generating audio, the skill sums measured clip durations and edits the
affected scripts if the total falls outside `duration ± 10%`.

## Voice selection

- **Windows:** list SAPI voices with

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .claude\skills\prompt2video\scripts\tts.ps1 -ListVoices
  ```

  Common picks: `Microsoft Zira Desktop` (English), `Microsoft Huihui Desktop`
  (Chinese).
- **macOS:** any `say` voice, e.g. `Samantha`, `Daniel`, `Ting-Ting`.
- If the requested voice is unavailable, the skill falls back to the closest
  installed voice for the same language.

## Examples

**English explainer, 90 seconds**

```text
topic: How large language models work
description: |
  Explain tokens, attention, and training in three acts, aimed at product
  managers who know no machine learning.
duration: 90s
scenes: 5
aspect: 16:9
style: corporate
tone: explanatory
audience: product managers
language: English
```

**Chinese vertical short with captions**

```text
topic: 为什么天空是蓝色的
description: |
  用瑞利散射解释天空为什么是蓝色的，结尾给一个日常类比。
duration: 45s
scenes: 3
aspect: 9:16
style: playful
voice: Microsoft Huihui Desktop
language: Chinese
captions: on
tone: casual
audience: 中学生
```

**Cinematic promo, one minute**

```text
topic: Launch of a habit-tracking app
description: |
  Three beats: the problem, the product reveal, the call to action.
duration: 60s
scenes: 4
aspect: 16:9
style: cinematic, gold accents
music: inspiring
language: English
```
