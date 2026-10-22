# usage: python analyze_style.py <video> <out_dir> [--transcribe] [--scene 0.3] [--model small]
# Measures the style of a video: shots/cut rhythm, palette, brightness/saturation/contrast,
# motion energy, loudness, speech rate and pauses. Writes out_dir/style_report.json,
# out_dir/shots/*.jpg (one middle frame per shot) and out_dir/sheets/*.png (timestamped contact sheets).
import sys, os, re, json, subprocess, shutil, argparse
import numpy as np
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('video')
ap.add_argument('out')
ap.add_argument('--transcribe', action='store_true')
ap.add_argument('--scene', type=float, default=0.3, help='scene-change threshold (lower = more cuts)')
ap.add_argument('--model', default='small', help='faster-whisper model size')
a = ap.parse_args()


def tool(name):
    p = shutil.which(name)
    if p:
        return p
    p = os.path.join(os.path.expanduser('~'), 'bin', name + ('.exe' if os.name == 'nt' else ''))
    if os.path.exists(p):
        return p
    sys.exit(f'{name} not found')


FFMPEG, FFPROBE = tool('ffmpeg'), tool('ffprobe')
os.makedirs(os.path.join(a.out, 'shots'), exist_ok=True)
os.makedirs(os.path.join(a.out, 'sheets'), exist_ok=True)


def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')


# --- basic stream info
probe = json.loads(run([FFPROBE, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', a.video]).stdout)
vs = next(s for s in probe['streams'] if s['codec_type'] == 'video')
has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
num, den = map(int, vs['r_frame_rate'].split('/'))
fps = num / den
duration = float(probe['format']['duration'])
W, H = int(vs['width']), int(vs['height'])

# --- shot detection + motion energy (scene score per frame)
res = run([FFMPEG, '-hide_banner', '-i', a.video, '-vf',
           'scale=320:-2,select=gte(scene\\,0),metadata=print:file=-', '-an', '-f', 'null', '-'])
times, scores = [], []
cur_t = None
for line in res.stdout.splitlines():
    m = re.search(r'pts_time:([\d.]+)', line)
    if m:
        cur_t = float(m.group(1))
    m = re.search(r'lavfi\.scene_score=([\d.]+)', line)
    if m and cur_t is not None:
        times.append(cur_t)
        scores.append(float(m.group(1)))
scores = np.array(scores) if scores else np.zeros(1)
cuts = [0.0]
for t, s in zip(times, scores):
    if s >= a.scene and t - cuts[-1] >= 0.25:
        cuts.append(t)
cuts.append(duration)
shots = [{'start': round(cuts[i], 3), 'end': round(cuts[i + 1], 3), 'dur': round(cuts[i + 1] - cuts[i], 3)}
         for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] > 0.05]
non_cut = scores[scores < a.scene]
motion = float(np.mean(non_cut)) if len(non_cut) else 0.0


# --- per-shot keyframe + colour stats
def grab(t, path):
    run([FFMPEG, '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=640:-2', path])


def palette(img, k=6):
    q = img.convert('RGB').resize((160, 90)).quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:k * 3]
    counts = sorted(q.getcolors(), reverse=True)
    return [{'hex': '#%02x%02x%02x' % tuple(pal[i * 3:i * 3 + 3]), 'share': round(c / (160 * 90), 3)}
            for c, i in counts]


all_px = []
bright, sat, contrast = [], [], []
for i, s in enumerate(shots):
    p = os.path.join(a.out, 'shots', f'shot_{i:03d}.jpg')
    grab(s['start'] + s['dur'] / 2, p)
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert('RGB')
    hsv = np.asarray(im.convert('HSV'), dtype=np.float32) / 255
    lum = np.asarray(im.convert('L'), dtype=np.float32) / 255
    s.update(frame=os.path.basename(p), palette=palette(im),
             brightness=round(float(lum.mean()), 3), saturation=round(float(hsv[..., 1].mean()), 3),
             contrast=round(float(lum.std()), 3))
    bright.append(s['brightness']); sat.append(s['saturation']); contrast.append(s['contrast'])
    all_px.append(np.asarray(im.resize((64, 36))))

global_palette = []
if all_px:
    mosaic = Image.fromarray(np.concatenate(all_px, axis=0))
    global_palette = palette(mosaic, 12)

# --- contact sheets: evenly spaced frames with timestamps (every ~duration/48, at least 2 s apart)
n = int(min(96, max(12, duration / 2)))
step = duration / n
sheet_frames = []
tmp = os.path.join(a.out, 'sheets', '_tmp.jpg')
for i in range(n):
    t = (i + 0.5) * step
    grab(t, tmp)
    if os.path.exists(tmp):
        im = Image.open(tmp).convert('RGB').resize((480, int(480 * H / W)))
        d = ImageDraw.Draw(im)
        label = f'{int(t // 60)}:{t % 60:05.2f}'
        d.rectangle([0, 0, 92, 22], fill=(0, 0, 0))
        d.text((5, 4), label, fill=(255, 255, 0))
        sheet_frames.append(im)
if os.path.exists(tmp):
    os.remove(tmp)
per = 12
for si in range(0, len(sheet_frames), per):
    group = sheet_frames[si:si + per]
    w, h = group[0].size
    sheet = Image.new('RGB', (w * 3, h * ((len(group) + 2) // 3)))
    for j, im in enumerate(group):
        sheet.paste(im, ((j % 3) * w, (j // 3) * h))
    sheet.save(os.path.join(a.out, 'sheets', f'sheet_{si // per + 1:02d}.png'))

# --- loudness
audio = {}
if has_audio:
    r = run([FFMPEG, '-hide_banner', '-i', a.video, '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    tail = r.stderr[r.stderr.rfind('Summary:'):]
    for key, pat in (('integrated_lufs', r'I:\s+(-?[\d.]+) LUFS'), ('loudness_range_lu', r'LRA:\s+(-?[\d.]+) LU'),
                     ('true_peak_dbfs', r'Peak:\s+(-?[\d.]+) dBFS')):
        m = re.search(pat, tail)
        if m:
            audio[key] = float(m.group(1))

# --- transcript, speech rate, pauses
speech = {}
if a.transcribe and has_audio:
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(a.model, device='cpu', compute_type='int8')
        # decode with ffmpeg ourselves: faster-whisper's PyAV path breaks on some installs
        pcm = subprocess.run([FFMPEG, '-v', 'error', '-i', a.video, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                             capture_output=True).stdout
        samples = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        segs, info = model.transcribe(samples, word_timestamps=True, vad_filter=True)
        words, lines = [], []
        for sg in segs:
            lines.append({'start': round(sg.start, 2), 'end': round(sg.end, 2), 'text': sg.text.strip()})
            words += [(w.start, w.end, w.word) for w in (sg.words or [])]
        gaps = [words[i + 1][0] - words[i][1] for i in range(len(words) - 1)]
        sent_gaps = [g for g in gaps if g > 0.25]
        speaking = sum(w[1] - w[0] for w in words)
        sentences = [x for x in re.split(r'(?<=[.!?])\s+', ' '.join(l['text'] for l in lines)) if x.strip()]
        speech = {
            'language': info.language,
            'word_count': len(words),
            'wpm_overall': round(len(words) / duration * 60, 1),
            'wpm_while_speaking': round(len(words) / max(speaking + sum(g for g in gaps if g <= 0.25), 1e-6) * 60, 1),
            'speech_coverage': round((words[-1][1] - words[0][0]) / duration, 3) if words else 0,
            'median_pause_s': round(float(np.median(sent_gaps)), 3) if sent_gaps else None,
            'avg_words_per_sentence': round(len(words) / max(len(sentences), 1), 1),
            'first_words_at_s': round(words[0][0], 2) if words else None,
        }
        with open(os.path.join(a.out, 'transcript.json'), 'w', encoding='utf-8') as f:
            json.dump(lines, f, indent=1, ensure_ascii=False)
        with open(os.path.join(a.out, 'transcript.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(f"[{l['start']:7.2f}] {l['text']}" for l in lines))
    except Exception as e:
        speech = {'error': str(e)}

durs = np.array([s['dur'] for s in shots])
report = {
    'video': os.path.abspath(a.video),
    'format': {'width': W, 'height': H, 'fps': round(fps, 3), 'duration_s': round(duration, 2)},
    'rhythm': {
        'shots': len(shots),
        'cuts_per_min': round((len(shots) - 1) / duration * 60, 2),
        'avg_shot_s': round(float(durs.mean()), 2),
        'median_shot_s': round(float(np.median(durs)), 2),
        'p10_shot_s': round(float(np.percentile(durs, 10)), 2),
        'p90_shot_s': round(float(np.percentile(durs, 90)), 2),
        'motion_energy': round(motion, 4),
    },
    'look': {
        'brightness': round(float(np.mean(bright)), 3) if bright else None,
        'saturation': round(float(np.mean(sat)), 3) if sat else None,
        'contrast': round(float(np.mean(contrast)), 3) if contrast else None,
        'global_palette': global_palette,
    },
    'audio': audio,
    'speech': speech,
    'shots': shots,
}
with open(os.path.join(a.out, 'style_report.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
print(json.dumps({k: report[k] for k in ('format', 'rhythm', 'audio', 'speech')}, indent=1, ensure_ascii=False))
print('palette:', ' '.join(c['hex'] for c in global_palette))
print('sheets:', len(sheet_frames), 'frames in', os.path.join(a.out, 'sheets'))
