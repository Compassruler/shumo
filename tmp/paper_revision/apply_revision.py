from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'tmp/paper_revision'
TARGET = ROOT / '26比赛/解题/初稿/MathModel.tex'
original = (WORK / 'MathModel.original.tex').read_bytes()
assert TARGET.read_bytes() == original, 'Main source changed since backup'
text = original.decode('utf-8').replace('\r\n', '\n')
operations = []

def replace_once(old, new, category):
    global text
    assert text.count(old) == 1, (category, text.count(old), old[:90])
    text = text.replace(old, new, 1)
    operations.append(dict(category=category, old=old, new=new))

proposal = json.loads((WORK / 'abstract_proposal.json').read_text(encoding='utf-8'))
abstract = proposal['abstract_latex']
assert '\\\\' not in abstract, 'Unexpected double backslash in abstract'
start = text.index('\\begin{abstract}') + len('\\begin{abstract}')
end = text.index('\\keywords{', start)
replace_once(text[start:end], '\n' + abstract + '\n', 'abstract')

def figure(stem, caption, label, width):
    return ('\\begin{center}\n'
            '\\begin{minipage}{\\textwidth}\n'
            '\\centering\n'
            f'\\includegraphics[width={width}\\textwidth]{{figures/{stem}.pdf}}\n'
            f'\\captionof{{figure}}{{{caption}}}\n'
            f'\\label{{{label}}}\n'
            '\\end{minipage}\n'
            '\\end{center}\n\n')

items = [
    ('\\section{模型假设}',
     '上述四个问题依次由单电池机理建模推进至电堆加载优化、恒功率辅助加热和动态反馈控制，前一问的模型与结论为后一问提供基础，其递进关系如图\\ref{fig:problem_progression}所示。',
     'problem_progression', '问题一至四的递进关系', 'fig:problem_progression', '1.0'),
    ('\\subsection{五片电堆瞬态自冷启动模型的建立}',
     '据此，本问先建立含端部热效应的五片电堆模型，再分别优化三类加载策略，并在统一启动判据下搜索最低可行初温，整体求解流程如图\\ref{fig:q2_startup_flowchart}所示。',
     'q2_startup_flowchart', '问题二：五片电堆瞬态自冷启动策略优化与最低初温搜索流程图', 'fig:q2_startup_flowchart', '1.0'),
    ('\\subsection{五片电堆辅助冷启动模型的建立}',
     '围绕上述权衡，本问在统一辅助冷启动模型下分别优化两类策略的分片功率与加热时长，再比较辅助能耗、启动速度及端部冰堵抑制效果，具体流程如图\\ref{fig:q3_heating_flowchart}所示。',
     'q3_heating_flowchart', '问题三：电堆辅助冷启动策略优化与对比流程图', 'fig:q3_heating_flowchart', '1.0'),
    ('\\subsection{电堆预冷与动态辅助冷启动模型的建立}',
     '上述思路形成了从预冷初场计算、闭环功率调节到策略比较与预冷影响分析的完整流程，如图\\ref{fig:q4_dynamic_flowchart}所示；下文依次给出模型、控制律及其数值验证。',
     'q4_dynamic_flowchart', '问题四：电堆动态辅助加热控制策略优化与预冷影响分析流程图', 'fig:q4_dynamic_flowchart', '0.78'),
]
for anchor, transition, stem, caption, label, width in items:
    replace_once(anchor, transition + '\n\n' + figure(stem, caption, label, width) + anchor, 'figure:'+stem)

TARGET.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
(WORK / 'operations.json').write_text(json.dumps(operations, ensure_ascii=False, indent=2), encoding='utf-8')
print('Updated abstract and inserted four figure blocks; all original line endings preserved.')
print('Original SHA256:', hashlib.sha256(original).hexdigest())
