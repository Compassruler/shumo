from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
from PIL import Image, ImageDraw
from pypdf import PdfReader

root = Path(r'D:\shumo\tmp\integrated_draft')
pdf = root / 'build' / 'MathModel.pdf'
out = root / 'preview'
out.mkdir(exist_ok=True)
poppler = Path(r'C:\Users\LENOVO\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin')
count = len(PdfReader(pdf).pages)

def render_range(chunk):
    first, last = chunk
    subprocess.run([str(poppler / 'pdftoppm.exe'), '-f', str(first), '-l', str(last), '-scale-to', '700', '-png', str(pdf), str(out / 'page')], check=True, capture_output=True)
    return chunk

chunks = [(i, min(i + 14, count)) for i in range(1, count + 1, 15)]
with ThreadPoolExecutor(max_workers=3) as pool:
    for chunk in pool.map(render_range, chunks):
        print(f'Rendered pages {chunk[0]}-{chunk[1]}', flush=True)

files = sorted(out.glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
for start in range(0, len(files), 12):
    sheet = Image.new('RGB', (4 * 370, 3 * 550), 'white')
    draw = ImageDraw.Draw(sheet)
    for j, path in enumerate(files[start:start + 12]):
        im = Image.open(path).convert('RGB')
        im.thumbnail((350, 510))
        x, y = (j % 4) * 370, (j // 4) * 550
        sheet.paste(im, (x + 10, y + 25))
        draw.text((x + 10, y + 6), f'PDF page {int(path.stem.split("-")[-1])}', fill='black')
    sheet.save(out / f'contact-{start // 12 + 1}.png')
print(f'PDF pages: {count}; contact sheets: {(count + 11) // 12}', flush=True)
