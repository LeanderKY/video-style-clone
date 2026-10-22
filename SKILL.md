---
name: video-style-clone
description: Clone the visual and editorial style of a reference video (usually a YouTube link) and produce a brand-new video in that exact style with the user's own script, voice, and topic. Use whenever the user shares a video/YouTube URL and says things like "make a video like this", "copy this style", "same quality as this video", "clone the style", "im Stil von", "so wie dieses Video", or wants their script turned into a video that looks and feels like a reference.
---

# Video Style Clone

Goal: a new video that a viewer would believe came from the same channel as the reference — same look,
pacing, motion language, sound design and quality bar — but with the user's own script, topic and voice.

**Clone the style, never the assets.** Do not reuse the reference's footage, characters, logos, music,
channel name or the creator's real voice. Recreate the *craft* (palette, shapes, typography, camera
language, editing rhythm, sound layering) with original material. If the user asks to clone a real
person's voice, only do it with that person's consent (their own voice is fine).

Always talk to the user in their language. All work lives in one project folder
(default: `~/Documents/<slug>`). `SKILL_DIR` below = the folder containing this file.

## Phase 0 — Inputs
Need: (1) reference URL, (2) the user's script or topic, (3) target length/format (16:9, 9:16 Shorts),
(4) language of the narration. If the script is missing, offer to write it in the reference's
storytelling structure. Only ask for what is truly missing.

## Phase 1 — Fetch the reference
```bash
python "SKILL_DIR/scripts/fetch_reference.py" "<URL>" "<project>/ref"
```
Downloads the video (≤1080p), info.json, thumbnail and subtitles (if any) into `ref/`.
If the download fails (age gate, region, login), ask the user for a local copy of the file instead.

## Phase 2 — Measure the style (objective)
```bash
python "SKILL_DIR/scripts/analyze_style.py" "<project>/ref/reference.mp4" "<project>/ref/analysis" --transcribe
```
Produces `analysis/style_report.json` + `analysis/sheets/*.png` + `analysis/shots/*.jpg`:
shot list and cut rhythm (avg/median shot length, cuts per minute), palette per shot and globally,
brightness/saturation/contrast, motion energy, loudness (LUFS), speech rate (words per minute),
pause lengths, and the transcript with timestamps (faster-whisper).

## Phase 3 — Look at it (subjective) and write the Style Bible
Read **every** contact sheet image in `analysis/sheets/` (they are in order, timestamps burned in) and
the transcript. Then fill `references/style_bible_template.md` into `<project>/STYLE_BIBLE.md`.
Be concrete and measurable — hex colours, px sizes at 1080p, stroke widths, easing curves, durations
in frames, how often the camera moves, what happens on every cut. Vague notes ("colourful, fun")
produce generic videos; the bible is what makes the clone exact.
Also study the structure: hook length, how sections open/close, joke density, question → answer
patterns, recurring segments, end card. See `references/style_dimensions.md` for the full checklist.

Show the user a short summary of the bible + 2–3 key observations and continue (don't block on it).

## Phase 4 — Adapt the script
Rewrite/shape the user's script to the reference's rhythm *without changing their content or meaning*:
same hook length, same sentence length distribution, same wpm target, same section structure,
visual beats every N seconds as measured. Output `scripts/script.tsv` (`id<TAB>speaker<TAB>pause_after<TAB>text`)
plus `design/storyboard.md` (one row per line: what is on screen, camera, SFX). Show the adapted script
to the user before voicing if wording changed noticeably.

## Phase 5 — Build
Pick the production method that matches the reference type:

| Reference looks like | Build with |
|---|---|
| 2D motion graphics / animated explainer (Kurzgesagt, TED-Ed, infographics) | **Remotion** (React + SVG), procedural or hand-built illustrations |
| Kinetic typography / text-heavy shorts | Remotion |
| Stock-footage / documentary edit | Remotion + user-supplied or AI-generated clips (ElevenLabs/Fish `generate_video`/`generate_image`, only after cost estimate + user OK) |
| Real-person talking head | Explain that this needs the user's own footage; clone grade, framing, captions and edit around it |

Proven template: `~/Documents/ifinity-invisible` (Remotion, timeline anchored to narration line ids,
procedural music/SFX, stills inspection, contact sheets). Copy its architecture
(`scripts/build_timeline.py`, `make_music.py`, `make_sfx.py`, `stills.mjs`, `src/lib.ts`, `src/theme.ts`)
instead of starting from zero — then restyle `theme.ts`, components and scenes to the Style Bible.

Rules that make it match:
- Put every token from the bible into `src/theme.ts` (palette, fonts, stroke widths, easing, durations). No ad-hoc colours.
- Match resolution, fps, and aspect ratio of the reference.
- Match measured cut rhythm: average shot length within ±15 % of the reference.
- Anchor every animation and sound cue to narration line ids so a voice swap re-times everything.
- Recreate the texture layer (grain, vignette, gradients, glow, paper texture, …) — this is most of the "quality" feel.
- Sound: narration on top, music ducked under voice, SFX on every visual event the reference would sound.

**Voice**: use the ElevenLabs or Fish Audio MCP tools (`creative_list_voices` / `search_voices`) to pick
a voice whose timbre, pace and energy match the reference narrator (not the same person).
Target the measured wpm; regenerate lines that miss it. Fallback: local TTS placeholders, swap later.

## Phase 6 — Quality loop (do not skip)
1. Render stills at the same relative timestamps as the reference sheets and build side-by-side sheets:
   `python "SKILL_DIR/scripts/side_by_side.py" <ref_sheet_dir> <our_stills_dir> <out.png>`
   Read them and list every visible difference (colour, line weight, density, text size, empty space).
2. Render the full video, then
   `python "SKILL_DIR/scripts/analyze_style.py" out/video.mp4 out/analysis` and
   `python "SKILL_DIR/scripts/compare_style.py" ref/analysis/style_report.json out/analysis/style_report.json`
   — fix every metric marked `OFF`.
3. Repeat until the comparison is all `OK`/`CLOSE` and the side-by-side shows no obvious tell.
   At least two full iterations. Write `design/review.md` with what was checked.

## Deliverable
`out/<slug>.mp4` (H.264/AAC, reference resolution, −14 LUFS for YouTube), the Style Bible, and a short
report: what matches, what deliberately differs (original characters/music), remaining gaps.
Send the video with SendUserFile. Never upload/publish anywhere without explicit permission.

Dependencies: Python 3 with `yt-dlp numpy pillow faster-whisper`, `ffmpeg`/`ffprobe` on PATH (or `~/bin`), Node 22 for Remotion.
