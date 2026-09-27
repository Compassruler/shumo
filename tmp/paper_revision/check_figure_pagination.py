from pathlib import Path
import subprocess
import os
import json
import re
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'tmp/paper_revision'
SOURCE=ROOT/'26比赛/解题/初稿'
text=(SOURCE/'MathModel.tex').read_text(encoding='utf-8')
start=text.index('\\begin{center}', text.index('\\end{itemize}'))
end=text.index('\\section{模型假设}', start)
block=text[start:end]
env=os.environ.copy()
font=(WORK/'fonts').as_posix()+'//'
env.update(OSFONTDIR=font,OPENTYPEFONTS=font+';',TEXINPUTS=font+';')
variants={
 'a':block.replace('\\clearpage\n',''),
 'b':block.replace('\\clearpage\n','').replace('width=1.0\\textwidth','width=0.90\\textwidth'),
 'c':block.replace('\\clearpage\n','').replace('width=1.0\\textwidth','width=0.80\\textwidth'),
 'd':'\\clearpage\n'+block.replace('\\clearpage\n',''),
}

def test(item):
 key,newblock=item
 d=WORK/'pagination'/key
 d.mkdir(parents=True,exist_ok=True)
 (d/'candidate.tex').write_text(text[:start]+newblock+text[end:],encoding='utf-8')
 for ext in ['aux','toc','out']:
  (d/('candidate.'+ext)).write_bytes((WORK/'build'/('MathModel.'+ext)).read_bytes())
 cmd=[r'D:\retex\CTEX\MiKTeX\miktex\bin\x64\xelatex.exe','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-jobname=candidate','-output-directory='+str(d),str(d/'candidate.tex')]
 p=subprocess.run(cmd,cwd=SOURCE,env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 output=p.stdout.decode('utf-8',errors='replace')
 (d/'compile.txt').write_text(output,encoding='utf-8')
 warnings=re.findall(r'Overfull[^\n]*',output)
 print(key,p.returncode,warnings,flush=True)
 return {'variant':key,'exit_code':p.returncode,'overfull':warnings,'figure_block':newblock}

with ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(test,variants.items()))
(WORK/'pagination/results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
