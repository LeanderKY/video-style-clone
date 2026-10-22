# usage: python side_by_side.py <reference_images_dir_or_files...> -- <our_images_dir_or_files...> <out.png>
#    or: python side_by_side.py <ref_dir> <ours_dir> <out.png>
# Pairs images in sorted order: reference on the left, ours on the right, one pair per row.
import sys, os, glob
from PIL import Image, ImageDraw


def collect(items):
    out = []
    for p in items:
        if os.path.isdir(p):
            out += sorted(f for f in glob.glob(os.path.join(p, '*')) if f.lower().endswith(('.png', '.jpg', '.jpeg')))
        else:
            out.append(p)
    return out


args = sys.argv[1:]
out = args.pop()
if '--' in args:
    i = args.index('--')
    ref, ours = collect(args[:i]), collect(args[i + 1:])
else:
    ref, ours = collect([args[0]]), collect([args[1]])
pairs = list(zip(ref, ours))
if not pairs:
    sys.exit('no image pairs')
W = 800
rows = []
for r, o in pairs:
    a, b = (Image.open(p).convert('RGB') for p in (r, o))
    a = a.resize((W, int(W * a.height / a.width)))
    b = b.resize((W, int(W * b.height / b.width)))
    row = Image.new('RGB', (W * 2 + 10, max(a.height, b.height)), (255, 0, 255))
    row.paste(a, (0, 0)); row.paste(b, (W + 10, 0))
    d = ImageDraw.Draw(row)
    d.rectangle([0, 0, 110, 20], fill=(0, 0, 0)); d.text((5, 4), 'REFERENCE', fill=(255, 255, 0))
    d.rectangle([W + 10, 0, W + 80, 20], fill=(0, 0, 0)); d.text((W + 15, 4), 'OURS', fill=(0, 255, 255))
    rows.append(row)
sheet = Image.new('RGB', (rows[0].width, sum(r.height + 10 for r in rows)), (255, 0, 255))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height + 10
sheet.save(out)
print(out, len(pairs), 'pairs')
