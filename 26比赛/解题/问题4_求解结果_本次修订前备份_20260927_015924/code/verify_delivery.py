"""Validate final local links, CSV deliverables, images and source provenance."""
import bootstrap
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote
import hashlib
import pandas as pd
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('href','src') and value:self.links.append(value)
def main():
    checks=[]
    def add(name,passed,detail):checks.append(dict(check=name,passed=bool(passed),detail=str(detail)))
    html=ROOT/'问题四_完整求解报告.html';parser=Links();parser.feed(html.read_text(encoding='utf-8-sig'))
    missing=[]
    for link in parser.links:
        if link.startswith(('#','https:','http:','data:')):continue
        if not (ROOT/unquote(link.split('#')[0])).exists():missing.append(link)
    add('report_local_links_exist',not missing,missing)
    png=list((ROOT/'figures').glob('*.png'));svg=list((ROOT/'figures').glob('*.svg'))
    add('13_png_and_13_svg',len(png)==13 and len(svg)==13,f'{len(png)}/{len(svg)}')
    for path in png:
        with Image.open(path) as image:
            add('image_readable_'+path.stem,min(image.size)>1000,str(image.size));image.verify()
    for name,count in [('main_results.csv',9),('constant_scan.csv',19),('guarded_results.csv',3),
                        ('robustness.csv',90),('guarded_robustness.csv',90),('coupled_convergence.csv',9)]:
        df=pd.read_csv(ROOT/'data'/name);add('rows_'+name,len(df)==count,len(df))
    for name in ('independent_export_validation.csv','model_validation.csv','precooling_validation.csv'):
        df=pd.read_csv(ROOT/'data'/name);add('checks_'+name,df.passed.all(),f'{df.passed.sum()}/{len(df)}')
    result=pd.DataFrame(checks);result.to_csv(ROOT/'data/delivery_validation.csv',index=False,encoding='utf-8-sig')
    manifest=[]
    files=[]
    for folder in ('code','inputs','audit'):
        files += [p for p in (ROOT/folder).iterdir() if p.is_file()]
    files += [ROOT/x for x in ('README.md','requirements.txt','run_all.ps1')]
    for path in sorted(files):manifest.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,
          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(manifest).to_csv(ROOT/'data/source_manifest.csv',index=False,encoding='utf-8-sig')
    print(f'Delivery validation: {result.passed.sum()}/{len(result)} passed; {len(manifest)} source files hashed')
    if not result.passed.all():print(result[~result.passed].to_string(index=False));raise SystemExit(1)
if __name__=='__main__':main()
