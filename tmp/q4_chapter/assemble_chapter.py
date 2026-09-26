from pathlib import Path
import re

work = Path(r'D:\shumo\tmp\q4_chapter')
out = Path(r'D:\shumo\26比赛\解题\2026建模比赛\第七章_问题四的分析与求解.tex')
p12 = (work / 'part71_72.tex').read_text(encoding='utf-8')
p3 = (work / 'part73.tex').read_text(encoding='utf-8')
p45 = (work / 'part74_75.tex').read_text(encoding='utf-8')
p12 = p12.replace('采用与前章一致的空间排列 $\\boldsymbol T=[T_{\\mathrm{EL}},T_1,T_2,T_3,T_4,T_5,T_{\\mathrm{ER}}]^{\\mathrm T}$', '为便于数值组装，将七节点状态排列为 $\\boldsymbol T=[T_1,T_2,T_3,T_4,T_5,T_{\\mathrm{EL}},T_{\\mathrm{ER}}]^{\\mathrm T}$')
p12 = p12.replace('并将预冷终态作为冷启动初态。', '并将预冷终态作为冷启动初态。以下物理方程中的温度统一采用开尔文，表格和图中的温度则用摄氏度表示；控制器中的温度差和温升速率不受温标平移影响，使用摄氏度实现时只需将冰点设为零。')
p3 = p3.replace('Q_L(', 'Q(').replace('\\lambda_i', 'k_i').replace('\\lambda_{i+1}', 'k_{i+1}').replace('\\lambda_b', 'k_b')
p3 = p3.replace('    \\label{B7-control-bounds}', '    \\vspace{0.3cm}\n    \\label{B7-control-bounds}')
p3 = p3.replace('    \\label{B7-control-parameters}', '    \\vspace{0.3cm}\n    \\label{B7-control-parameters}')
last = max(map(int, re.findall(r'\\tag\{7-(\d+)\}', p12)))
p3 = re.sub(r'7-@@(\d+)@@', lambda m: f'7-{last+int(m[1])}', p3)
last = max(map(int, re.findall(r'\\tag\{7-(\d+)\}', p3)))
p45 = re.sub(r'7-@@R(\d+)@@', lambda m: f'7-{last+int(m[1])}', p45)
preamble = r'''% !TeX program = xelatex
% 编码：UTF-8。本文仅含第七章，可在当前目录使用 XeLaTeX 编译。
% 排版沿用 MathModel.tex 的 gmcmthesis 类；不含封面、摘要及其他章节。
% 图形直接引用 ../问题4_求解结果/figures/ 中的原始 PDF，无需复制或重画。
% 合并主论文时，取“第七章正文开始”至“第七章正文结束”之间的内容，
% 并在主论文导言区保留下列 graphicspath；表号按主论文原有序列自动衔接。
\documentclass[bwprint]{gmcmthesis}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{geometry}
\usepackage{graphicx}
\geometry{a4paper,left=2cm,right=2cm,margin=2.5cm}
\numberwithin{figure}{section}
\renewcommand{\thefigure}{\arabic{section}-\arabic{figure}}
\graphicspath{{../问题4_求解结果/figures/}}
\begin{document}
\setcounter{section}{6}
\setcounter{table}{8}
% 第七章正文开始
\section{问题四的分析与求解}

'''
text = preamble + p12 + '\n' + p3 + '\n' + p45 + '\n% 第七章正文结束\n\\end{document}\n'
out.write_text(text, encoding='utf-8')
tags=list(map(int,re.findall(r'\\tag\{7-(\d+)\}',text)))
labels=re.findall(r'\\label\{([^}]+)\}',text)
refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',text)
assert tags==list(range(1,len(tags)+1)), tags
assert len(labels)==len(set(labels)), 'duplicate labels'
assert not set(refs)-set(labels), set(refs)-set(labels)
assert '@@' not in text
assert not re.search(r'(?<!\\)\\\[|\$\$|\\begin\{(?:align\*|equation\*|displaymath)\}',text)
figures=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',text)
figdir=out.parent.parent/'问题4_求解结果'/'figures'
assert all((figdir/f).exists() for f in figures), figures
print({'path':str(out),'formulas':len(tags),'figures':len(figures),'tables':text.count('\\begin{table}'),'chars':len(text),'subsections':re.findall(r'\\subsection\{([^}]+)\}',text)})
