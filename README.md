# video-style-clone

A [Claude Code](https://claude.com/claude-code) skill that clones the visual and editorial style of a reference
video (e.g. a YouTube link) and produces a new video in that style with your own script, topic and voice.

It clones the **style**, never the assets: footage, characters, music, logos and the creator's voice are
recreated as original material.

## What it does

1. **Fetch** the reference (video ≤1080p, metadata, thumbnail, subtitles) — `scripts/fetch_reference.py`
2. **Measure** the style: shots and cut rhythm, palette, brightness/saturation/contrast, motion energy,
   loudness, speech rate, pauses, transcript, timestamped contact sheets — `scripts/analyze_style.py`
3. **Write a Style Bible** with concrete values (hex colours, sizes, easing, durations, structure) —
   `references/style_bible_template.md`, `references/style_dimensions.md`
4. **Adapt your script** to the reference's rhythm without changing its content
5. **Build** the video (Remotion for motion graphics), voice via ElevenLabs / Fish Audio
6. **Quality loop**: side-by-side frames (`scripts/side_by_side.py`) and a metric comparison
   (`scripts/compare_style.py`, OK / CLOSE / OFF) until nothing is off

## Install

```bash
git clone <this repo> ~/.claude/skills/video-style-clone
pip install yt-dlp numpy pillow faster-whisper
```

Also needs `ffmpeg`/`ffprobe` on PATH (or in `~/bin`) and Node 22 for Remotion.

Then in Claude Code: *"Make a video in the style of <URL> with this script: …"*

## Script usage

```bash
python scripts/fetch_reference.py <url> <project>/ref
python scripts/analyze_style.py <project>/ref/reference.mp4 <project>/ref/analysis --transcribe
python scripts/compare_style.py ref/analysis/style_report.json out/analysis/style_report.json
python scripts/side_by_side.py <ref_frames_dir> <our_frames_dir> out.png
```
