# usage: python fetch_reference.py <url> <out_dir>
# Downloads the reference video (<=1080p, mp4), info.json, thumbnail and subtitles into out_dir/.
import sys, os, json, shutil, glob
import yt_dlp

url, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

home_bin = os.path.join(os.path.expanduser('~'), 'bin')
ffmpeg_dir = home_bin if os.path.exists(os.path.join(home_bin, 'ffmpeg.exe')) else None

opts = {
    'outtmpl': os.path.join(out, 'reference.%(ext)s'),
    'format': 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b',
    'merge_output_format': 'mp4',
    'writeinfojson': True,
    'writethumbnail': True,
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'noprogress': True,
}
if ffmpeg_dir:
    opts['ffmpeg_location'] = ffmpeg_dir

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=True)

# subtitles in a separate pass: they are optional and often rate-limited (HTTP 429)
lang = (info.get('language') or 'en').split('-')[0]
sub_opts = dict(opts, skip_download=True, writeinfojson=False, writethumbnail=False,
                writesubtitles=True, writeautomaticsub=True, subtitlesformat='vtt',
                subtitleslangs=sorted({lang, 'en', 'de'}))
try:
    with yt_dlp.YoutubeDL(sub_opts) as ydl:
        ydl.download([url])
except Exception as e:
    print('subtitles skipped:', str(e).splitlines()[0])

video = os.path.join(out, 'reference.mp4')
if not os.path.exists(video):
    cands = [p for p in glob.glob(os.path.join(out, 'reference.*'))
             if p.rsplit('.', 1)[-1] in ('mp4', 'mkv', 'webm')]
    if not cands:
        sys.exit('download failed - ask the user for a local copy of the video')
    shutil.move(cands[0], video)

summary = {k: info.get(k) for k in ('title', 'channel', 'duration', 'width', 'height', 'fps',
                                     'upload_date', 'view_count', 'description', 'chapters', 'tags')}
summary['url'] = url
summary['subtitles'] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(out, '*.vtt')))
with open(os.path.join(out, 'meta.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(json.dumps({k: summary[k] for k in ('title', 'channel', 'duration', 'width', 'height', 'fps', 'subtitles')},
                 ensure_ascii=False))
