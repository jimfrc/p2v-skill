---
name: prompt2video
description: Generate a short narrated video from a prompt using Remotion. The video topic is provided in the first prompt. Produces an MP4, per-scene voice-over audio (macOS `say` + ffmpeg, or Windows PowerShell System.Speech), and a multi-page slides PDF (one still per scene). Trigger when the user asks to "generate/render/build a video", "make a video from a prompt", "render with Remotion", "create voice-over", or to produce slides/PDF from the video scenes.
---

# prompt2video
- Generate a video based on the user description, honoring any optional prompt controls (see "Prompt controls").
- Add a voice-over narration track.
- Default to 1–2 minutes long; override with the `duration` control.
- Generate a PDF of slides (one page per scene).

## Platform support
The workflow is identical on macOS and Windows; only the TTS and PDF steps differ. Helper scripts live next to this file in `scripts/`.

| Step | macOS | Windows |
|---|---|---|
| Voice-over | `say` → AIFF → MP3 with `ffmpeg` | `scripts/tts.ps1` (built-in System.Speech) → WAV |
| Audio duration | `ffprobe` | `node scripts/wav-duration.mjs <file.wav>` |
| Slides PDF | `magick` **or** `scripts/images-to-pdf.mjs` | `scripts/images-to-pdf.mjs` (needs `npm install pdf-lib`) |

On Windows, all commands below are run from the project root in PowerShell or cmd. The helper scripts are at `.claude/skills/prompt2video/scripts/` when this skill was installed into a generated project. Use `ffprobe`/`ffmpeg`/`magick` on Windows only if they are actually on `PATH`.

## Prompt controls
The prompt may include optional control keys, usually as `key: value` lines alongside `topic:`/`description:`. **Every key is optional** — when one is absent, use the default. Honor any that appear; if the prompt gives free-text instructions instead (e.g. "make it about a minute, vertical, for kids"), infer the equivalent controls.

| Key | Meaning | Default | How to apply |
|---|---|---|---|
| `duration` | target total length, e.g. `90s`, `2m` | 1–2 min | Drives the total word budget; verify with the measured audio duration (see "Hitting the target duration"). |
| `scenes` | number of scenes / slides | your choice, ~4–6 | Produce exactly this many `<Sequence>`s and PDF pages; split the word budget across them. |
| `aspect` | frame shape: `16:9`, `9:16`, `1:1` | `16:9` | Set the composition `width`/`height` (see table below) before writing components. |
| `style` | visual look — a preset name and/or free-form descriptors | `clean` preset | Apply the matching preset's design tokens; layer free-form descriptors on top. |
| `voice` | TTS voice name: a macOS `say` voice (`Samantha`, `Daniel`) or a Windows SAPI voice (`Microsoft Zira Desktop`, `Microsoft Huihui Desktop`) | system default | macOS: `say -v <voice>`; Windows: `tts.ps1 -Voice "<voice>"`. If the requested voice is not installed for this platform, pick the closest installed voice for the same language. |
| `rate` | speech rate in words-per-minute | 175 | macOS: `say -r <rate>`; Windows: `tts.ps1 -Wpm <rate>`. Also update the words↔seconds math. |
| `tone` | narration register, e.g. `casual`, `formal`, `enthusiastic` | neutral / explanatory | Shape the wording of the narration scripts. |
| `audience` | reading level / who it's for, e.g. `kids`, `experts` | general | Shape vocabulary and depth. |
| `language` | narration + on-screen language | English | Write scripts in this language; pick a TTS voice matching it. |
| `captions` | burn per-scene subtitles on screen: `on` / `off` | `off` | Render the scene text as an on-screen caption element. |
| `music` | background-music mood, or `off` | `off` | If enabled, mix a bed track under the narration at low volume. |

### Aspect → composition size
Set these on the `<Composition>` (in `src/Root.tsx` / `src/index.ts`) before building scenes, and design each scene's layout for the chosen shape (e.g. stacked / centered for `9:16`):

| `aspect` | width × height |
|---|---|
| `16:9` (default) | 1920 × 1080 |
| `9:16` | 1080 × 1920 |
| `1:1` | 1080 × 1080 |

## Visual style presets
`style` selects a preset (and/or free-form descriptors). Apply the preset's tokens consistently across **every** scene so the video looks cohesive; free-form descriptors (e.g. `neon accents`, `hand-drawn`, specific brand hex colors) override individual tokens.

| Preset | Background | Text / accent | Font family | Transitions |
|---|---|---|---|---|
| `clean` (default) | white / very light gray | near-black text, one blue accent | system sans (Inter / Helvetica) | quick fade + subtle slide |
| `dark` | near-black / deep navy | off-white text, neon-cyan accent | geometric sans | fade + soft glow |
| `corporate` | white with thin rule lines | navy + slate, muted accent | serif headings + sans body | crisp cut / short fade |
| `playful` | warm pastel | high-contrast bold color, rounded shapes | rounded sans (Poppins) | bouncy spring |
| `cinematic` | black with letterbox bars | white serif, gold accent | display serif | slow fade + ken-burns zoom |

### Hitting the target duration
Total video length is driven by total voice-over length (each `<Sequence>` is sized from its audio clip's duration). At narration rate `R` wpm (default 175), total words ≈ `duration_seconds × R / 60`:
- 60s @ 175 wpm → ~175 words across all scene `.txt` files combined
- 90s @ 175 wpm → ~260 words combined
- 120s @ 175 wpm → ~350 words combined

Budget words per scene roughly proportional to its importance, split across the requested `scenes` count. After generating the audio files, sum their measured durations and **verify against the target**: if the total falls outside `duration ± 10%`, edit the scene scripts (add or trim sentences) and regenerate the affected clips until it lands. Pinning the speech rate (`say -r` on macOS, `-Wpm` on Windows) keeps the words↔seconds mapping predictable.

## Workflow
Run these steps in order:
1. **Read the prompt controls** (see "Prompt controls"): set the composition `width`/`height` from `aspect`, the target scene count from `scenes`, and the target length from `duration`; pick the `style` preset tokens.
2. Write per-scene narration text and generate per-scene audio clips (see "How to Generate Voice-over Narration" below), honoring `voice`, `rate`, `tone`, `audience`, and `language`.
3. Wire each `<Audio>` + `<Sequence>` pair into `src/Composition.tsx`, using the measured per-scene durations and the chosen `style` preset tokens.
4. Render the MP4 with `npx remotion render`.
5. Extract one still per scene and assemble them into `out/slides.pdf` (see "Slides Generation into PDF").

## How to Generate Voice-over Narration
Generate a voice-over audio track for the video, split per scene, then measure each clip so the Remotion `<Sequence>`s can be sized from it.

Steps:
1. Write one text file per scene under `public/scenes/` (e.g. `scene1.txt` … `sceneN.txt`), one file per requested scene. Write them as UTF-8 (the Write tool does this). Use short, spoken-friendly sentences shaped by any `tone`, `audience`, and `language` controls. Replace symbols and underscores with spoken forms (e.g. write "a11y parse" instead of "a11y_parse").

2. For each scene file, generate the audio. Add the voice and/or rate when the prompt sets `voice`/`rate`.

   **macOS** (`say`, then convert to MP3 with ffmpeg):
   ```bash
   say [-v <voice>] [-r <rate>] -f public/scenes/sceneN.txt -o public/scenes/sceneN.aiff
   ffmpeg -y -i public/scenes/sceneN.aiff public/scenes/sceneN.mp3
   ```

   **Windows** (built-in System.Speech via the bundled PowerShell helper; run each command on a single line):
   ```bash
   powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/prompt2video/scripts/tts.ps1 -TextFile public/scenes/sceneN.txt -OutFile public/scenes/sceneN.wav [-Voice "<voice>"] [-Wpm <rate>]
   ```
   - List installed voices: `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/prompt2video/scripts/tts.ps1 -ListVoices`
   - Pick a voice whose language matches `language` (e.g. `Microsoft Huihui Desktop` for Chinese, `Microsoft Zira Desktop` for English). If `voice` names a macOS voice that does not exist here, use the closest matching installed voice; if nothing matches, omit `-Voice`.
   - WAV output is fine for Remotion; no MP3 conversion is needed on Windows.

3. Read each scene's duration in seconds:
   - macOS: `ffprobe -v error -show_entries format=duration -of csv=p=0 public/scenes/sceneN.mp3`
   - Windows: `node .claude/skills/prompt2video/scripts/wav-duration.mjs public/scenes/sceneN.wav`

4. Convert seconds → frames using the composition's `fps` (e.g. `Math.ceil(seconds * fps)`), then use those frame counts to size each `<Sequence>` in the Remotion composition. Layer each `public/scenes/sceneN.wav` (or `.mp3`) as an `<Audio>` (from `@remotion/media`) inside its corresponding `<Sequence>`, using `staticFile('scenes/sceneN.wav')` (or `staticFile('scenes/sceneN.mp3')`), so each scene plays its own narration.

Output: `public/scenes/sceneN.wav` (Windows) or `public/scenes/sceneN.mp3` (macOS), one per scene.


## Slides Generation into PDF 
After the Remotion video is generated, create still slides at the end of each scene and assemble them into a PDF.

1. Read `src/Composition.tsx` to extract:
   - Each scene's duration in frames (e.g. SCENE1_FRAMES, SCENE2_FRAMES, …)
   - Each scene's offset in the composition (cumulative sum of prior durations)
   - The fade-out duration used by `fadeInOut(frame, durationInFrames, fadeFrames)` — typically 18 frames
   - The composition id and entry file (e.g. `MyComp` in `src/index.ts`)

2. For each scene N, compute the capture frame as the last fully-opaque frame BEFORE the fade-out begins:
   - `captureFrameN = sceneOffsetN + sceneDurationN - fadeFrames - 1`
   - This ensures the slide shows the scene fully rendered, with all in-scene animations settled and no fade transparency.

3. Render one PNG per scene with Remotion's still command:
    - `npx remotion still <entry> <comp-id> out/sceneN.png --frame=<captureFrameN> --image-format=png`
    - Run sequentially (or chained with &&) so the bundle is reused. 
    - Output goes to `out/scene1.png` … `out/sceneN.png` at the composition's native resolution (e.g. 1920×1080).

4. Combine the PNGs into a single multi-page PDF, in scene order. Preferred, and the only option on Windows:
    - `npm install pdf-lib` once in the project root (skip if `pdf-lib` is already in `package.json`)
    - `node .claude/skills/prompt2video/scripts/images-to-pdf.mjs out/slides.pdf out/scene1.png out/scene2.png … out/sceneN.png`
   On macOS with ImageMagick installed you may instead use:
    - `magick out/scene1.png out/scene2.png … out/sceneN.png out/slides.pdf`
5. Verify `out/slides.pdf` exists and report the per-scene capture frames plus the PDF path back to the user.
