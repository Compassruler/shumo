from pathlib import Path
import json
import re
import difflib
import hashlib

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'tmp/paper_revision'
SOURCE=ROOT/'26比赛/解题/初稿'
original=(WORK/'MathModel.original.tex').read_bytes()
current=(SOURCE/'MathModel.tex').read_bytes()
old=original.decode('utf-8').replace('\r\n','\n')
new=current.decode('utf-8').replace('\r\n','\n')
ops=json.loads((WORK/'operations.json').read_text(encoding='utf-8'))
restored=new
for op in reversed(ops):
    assert restored.count(op['new'])==1,op['category']
    restored=restored.replace(op['new'],op['old'],1)
assert restored.replace('\n','\r\n').encode('utf-8')==original
assert re.search(r'\\keywords\{[^\n]+',old).group()==re.search(r'\\keywords\{[^\n]+',new).group()
before_bib=new.split(r'\begin{thebibliography}',1)[0]
order=[]
for match in re.finditer(r'\\cite\{([^}]+)\}',before_bib):
    for key in match.group(1).split(','):
        if key not in order:
            order.append(key)
bib_order=re.findall(r'\\bibitem\{([^}]+)\}',new)
assert order==bib_order and len(order)==18
assert len(set(re.findall(r'\\label\{([^}]+)\}',new)))==len(re.findall(r'\\label\{([^}]+)\}',new))
abstract=json.loads((WORK/'abstract_final.json').read_text(encoding='utf-8'))
assert [len(re.sub(r'\s+','',p)) for p in abstract['plain_text']]==[108,405,315,72]
assert abstract['latex'] in new

audit=json.loads((WORK/'source_audit.json').read_text(encoding='utf-8'))
audit.update(original_sha256=hashlib.sha256(original).hexdigest(),final_sha256=hashlib.sha256(current).hexdigest(),
             original_bytes_recovered_exactly=True,keywords_unchanged=True,citation_order_matches_bibliography=True,
             abstract_counts=abstract['counts'],abstract_percentages=abstract['percentages'],
             figure_labels=['fig:problem_progression','fig:q2_startup_flowchart','fig:q3_heating_flowchart','fig:q4_dynamic_flowchart'],
             change_categories=[x['category'] for x in ops])

log=(WORK/'compile-final.txt').read_text(encoding='utf-8',errors='replace')
for bad in ['Overfull', 'There were undefined references', 'multiply defined', 'Missing character', 'Label(s) may have changed', '! LaTeX Error']:
    assert bad not in log,bad
aux=(WORK/'build/MathModel.aux').read_text(encoding='utf-8')
figs=[]
for key in audit['figure_labels']:
    m=re.search(r'\\newlabel\{'+re.escape(key)+r'\}\{\{([^}]+)\}\{([^}]+)\}',aux)
    assert m,key
    figs.append({'key':key,'number':m[1],'printed_page':int(m[2]),'pdf_page':int(m[2])+1})
assert [r['number'] for r in figs]==['1-1','5-1','6-1','7-1']
for n,key in enumerate(order,1):
    assert r'\bibcite{'+key+'}{'+str(n)+'}' in aux,(key,n)
audit.update(figures=figs,final_compile_exit_code=0,undefined_references=0,overfull_boxes=0)
(WORK/'source_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'authorized_changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/MathModel.tex',tofile='revised/MathModel.tex',n=2)),encoding='utf-8')
print('Final source, citation order, abstract proportions, unique labels and compilation checks passed.')
print(json.dumps(figs,ensure_ascii=True))
