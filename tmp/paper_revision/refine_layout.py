from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'tmp/paper_revision'
TARGET = ROOT / '26比赛/解题/初稿/MathModel.tex'
text = TARGET.read_bytes().decode('utf-8').replace('\r\n','\n')
ops = json.loads((WORK/'operations.json').read_text(encoding='utf-8'))

def replace_once(old,new,category):
    global text
    assert text.count(old)==1, (category, text.count(old))
    text=text.replace(old,new,1)
    ops.append(dict(category=category,old=old,new=new))

plain=json.loads((WORK/'abstract_900_draft.json').read_text(encoding='utf-8'))
plain[1]=plain[1].replace('所搜索策略的','所用策略的').replace('区分首次达标与实际关热事件','区分首次达标与关热事件')
plain[3]=plain[3].replace('启动不保证','首次达标不保证').replace('结论限于考察模型与策略','结论限于模型与策略')
counts=[len(''.join(s.split())) for s in plain]
assert counts==[108,405,315,72], counts

def to_latex(s):
    s=s.replace('−','-').replace('—','--').replace('%',r'\%')
    def unit(m):
        number,u=m.groups()
        if u=='℃':
            return '$'+number+r'\,^\circ\mathrm C$'
        return '$'+number+r'\,\mathrm{'+u+'}$'
    return re.sub(r'(-?\d+(?:\.\d+)?)\s+(℃|J|s|min)\b' if False else r'(-?\d+(?:\.\d+)?)\s+(℃|min|J|s)',unit,s)

latex='\n\n'.join(to_latex(s) for s in plain)
a=text.index(r'\begin{abstract}')+len(r'\begin{abstract}')
b=text.index(r'\keywords{',a)
replace_once(text[a:b],'\n'+latex+'\n','abstract:fit-one-page')

for stem in ['problem_progression','q2_startup_flowchart','q3_heating_flowchart','q4_dynamic_flowchart']:
    initial=next(x for x in ops if x['category']=='figure:'+stem)
    # Keep the introduction and the inserted graphic together, without touching surrounding prose.
    block=initial['new']
    transition,tail=block.split('\n\n',1)
    revised=tail.replace('\\begin{minipage}{\\textwidth}\n\\centering', '\\begin{minipage}{\\textwidth}\n\\setlength{\\parindent}{2em}\n'+transition+'\\par\\medskip\n\\centering',1)
    if stem=='problem_progression':
        revised=revised.replace('\\end{center}\n\n', '\\end{center}\n\\clearpage\n\n',1)
    replace_once(block,revised,'figure-layout:'+stem)

TARGET.write_bytes(text.replace('\n','\r\n').encode('utf-8'))
(WORK/'operations.json').write_text(json.dumps(ops,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'abstract_final.json').write_text(json.dumps({'count_rule':'Unicode characters excluding whitespace; units normalized as shown in plain_text; LaTeX commands, title and keywords excluded.','counts':counts,'percentages':[12,45,35,8],'total':900,'plain_text':plain,'latex':latex},ensure_ascii=False,indent=2),encoding='utf-8')
original=(WORK/'MathModel.original.tex').read_bytes().decode('utf-8').replace('\r\n','\n')
restored=text
for op in reversed(ops):
    assert restored.count(op['new'])==1,op['category']
    restored=restored.replace(op['new'],op['old'],1)
assert restored==original
print('Abstract: 108 / 405 / 315 / 72 = 12% / 45% / 35% / 8%.')
print('Only abstract and newly inserted figure blocks refined; all other content preserved.')
