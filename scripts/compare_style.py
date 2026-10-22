# usage: python compare_style.py <reference style_report.json> <ours style_report.json>
# Prints each metric with reference vs ours and OK / CLOSE / OFF.
import sys, json

ref, ours = (json.load(open(p, encoding='utf-8')) for p in sys.argv[1:3])

# (section, key, tolerance for OK as relative difference, CLOSE = 2x tolerance)
checks = [
    ('format', 'width', 0), ('format', 'height', 0), ('format', 'fps', 0.01),
    ('rhythm', 'avg_shot_s', 0.15), ('rhythm', 'median_shot_s', 0.15), ('rhythm', 'cuts_per_min', 0.15),
    ('rhythm', 'motion_energy', 0.30),
    ('look', 'brightness', 0.10), ('look', 'saturation', 0.12), ('look', 'contrast', 0.15),
    ('speech', 'wpm_while_speaking', 0.08), ('speech', 'median_pause_s', 0.25),
    ('speech', 'avg_words_per_sentence', 0.20), ('speech', 'speech_coverage', 0.10),
    ('audio', 'loudness_range_lu', 0.35),
]
off = 0
print(f"{'metric':32} {'reference':>10} {'ours':>10}  verdict")
for sec, key, tol in checks:
    r, o = ref.get(sec, {}).get(key), ours.get(sec, {}).get(key)
    if not isinstance(r, (int, float)) or not isinstance(o, (int, float)):
        continue
    diff = abs(o - r) / max(abs(r), 1e-6)
    verdict = 'OK' if diff <= tol else 'CLOSE' if diff <= 2 * tol else 'OFF'
    off += verdict == 'OFF'
    print(f'{sec + "." + key:32} {r:>10} {o:>10}  {verdict}' + (f'  ({o - r:+.3g})' if verdict != 'OK' else ''))

lufs = ours.get('audio', {}).get('integrated_lufs')
if lufs is not None:
    v = 'OK' if abs(lufs + 14) <= 1 else 'OFF'
    off += v == 'OFF'
    print(f"{'audio.integrated_lufs (-14 target)':32} {ref.get('audio', {}).get('integrated_lufs', '-'):>10} {lufs:>10}  {v}")


def hexes(rep):
    return [c['hex'] for c in rep.get('look', {}).get('global_palette', [])]


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


rp, op = hexes(ref), hexes(ours)
if rp and op:
    print('\npalette match (each reference colour -> nearest of ours, distance 0-441):')
    for h in rp:
        best = min(op, key=lambda x: sum((a - b) ** 2 for a, b in zip(rgb(h), rgb(x))))
        d = sum((a - b) ** 2 for a, b in zip(rgb(h), rgb(best))) ** 0.5
        print(f'  {h} -> {best}  {d:5.1f}  {"OK" if d < 30 else "CLOSE" if d < 60 else "OFF"}')
print(f'\n{off} metric(s) OFF')
