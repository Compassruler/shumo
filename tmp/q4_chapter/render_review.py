from pathlib import Path
import subprocess
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

root=Path(r'D:\shumo\tmp\q4_chapter')
pdf=root/'compile'/'第七章_问题四的分析与求解.pdf'
out=root/'page_review'
out.mkdir(exist_ok=True)
subprocess.run(['pdftoppm','-scale-to','1400','-png',str(pdf),str(out/'page')],check=True,capture_output=True)
pages=sorted(out.glob('page-*.png'))
for off in range(0,len(pages),6):
    chunk=pages[off:off+6]
    sheet=Image.new('RGB',(1200,1740),'#dddddd')
    d=ImageDraw.Draw(sheet)
    for j,p in enumerate(chunk):
        im=Image.open(p).convert('RGB')
        im.thumbnail((390,830))
        x=400*(j%3)+(400-im.width)//2
        y=870*(j//3)+25
        sheet.paste(im,(x,y))
        d.text((400*(j%3)+10,870*(j//3)+5),p.stem,fill='black')
    sheet.save(out/f'contact-{off//6+1}.png')
r=PdfReader(str(pdf))
lines=[]
for i,p in enumerate(r.pages,1):
    text=p.extract_text() or ''
    lines.append(f'PAGE {i}: '+text[:110].replace('\n',' '))
    if '??' in text: lines.append('POSSIBLE UNRESOLVED REF')
(root/'page_summary.txt').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
