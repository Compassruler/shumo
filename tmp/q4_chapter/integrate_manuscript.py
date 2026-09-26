from pathlib import Path
import hashlib
import json
import re
import shutil

base = Path(r'D:\shumo\26比赛\解题')
source_dir = base / '2026建模比赛'
out_dir = base / '初稿'
audit_dir = Path(r'D:\shumo\tmp\integrated_draft')
audit_dir.mkdir(parents=True, exist_ok=True)
out_dir.mkdir(exist_ok=True)
main_path = source_dir / 'MathModel.tex'
chapter_path = source_dir / '第七章_问题四的分析与求解.tex'
main_bytes, chapter_bytes = main_path.read_bytes(), chapter_path.read_bytes()
main = main_bytes.decode('utf-8')
chapter = chapter_bytes.decode('utf-8')
newline = '\r\n' if '\r\n' in main else '\n'

body_start = chapter.index(r'\section{问题四的分析与求解}')
body_end = chapter.index('% 第七章正文结束')
chapter_body = chapter[body_start:body_end]
start = main.index(r'\section{问题四的分析与求解}')
end = main.index(r'\section{模型的评价}', start)
assert main.count(r'\section{问题四的分析与求解}') == 1
assert chapter_body.count(r'\section{') == 1
assert r'\setcounter' not in chapter_body

kept_prefixes = (r'\noindent 时认为当前时间步收敛。', r'\noindent 时，说明当前时间步跨越了五片共同过零事件。')
removed = []
lines = main.splitlines(keepends=True)
for index, line in enumerate(lines):
    if r'\noindent' in line and not line.startswith(kept_prefixes):
        assert line.startswith(r'\noindent '), (index + 1, line)
        lines[index] = line.replace(r'\noindent', '', 1)
        removed.append(index + 1)
indented = ''.join(lines)
assert len(removed) == 199
assert indented.count(r'\noindent') == 2
start = indented.index(r'\section{问题四的分析与求解}')
end = indented.index(r'\section{模型的评价}', start)
merged_without_setup = indented[:start] + chapter_body + indented[end:]
setup = (r'% 列表条目中的后续正文段落与普通正文保持两字首行缩进。' + newline
         + r'\setlist[itemize]{listparindent=2em}' + newline)
merged = merged_without_setup.replace(r'\begin{document}', setup + r'\begin{document}', 1)
output_tex = out_dir / 'MathModel.tex'
assert not output_tex.exists(), 'Do not overwrite an existing draft.'
output_tex.write_bytes(merged.encode('utf-8'))

def active_tex(text):
    return '\n'.join(re.split(r'(?<!\\)%', line, maxsplit=1)[0] for line in text.splitlines())

graphic_pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}'
main_figures = re.findall(graphic_pattern, active_tex(main))
chapter_figures = re.findall(graphic_pattern, active_tex(chapter_body))
copied = []

def copy_asset(src, dst):
    assert src.is_file(), src
    if dst.exists():
        assert dst.read_bytes() == src.read_bytes(), f'Asset collision: {dst}'
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    assert src.read_bytes() == dst.read_bytes()
    copied.append({'source': str(src), 'destination': str(dst), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest()})

for filename in dict.fromkeys(main_figures):
    copy_asset(source_dir / filename, out_dir / filename)
for filename in dict.fromkeys(chapter_figures):
    copy_asset(base / '问题4_求解结果' / 'figures' / filename, out_dir / filename)
copy_asset(source_dir / 'gmcmthesis.cls', out_dir / 'gmcmthesis.cls')
for filename in ('picture.eps', 'wenzi.eps'):
    copy_asset(source_dir / 'figures' / filename, out_dir / 'figures' / filename)

labels = re.findall(r'\\label\{([^{}]+)\}', active_tex(merged))
refs = re.findall(r'\\(?:ref|eqref|pageref)\{([^{}]+)\}', active_tex(merged))
assert len(labels) == len(set(labels)), 'Duplicate cross-reference labels.'
assert not (set(refs) - set(labels)), set(refs) - set(labels)
assert re.findall(r'\\tag\{(7-\d+)\}', chapter_body) == [f'7-{i}' for i in range(1, 48)]
assert main_path.read_bytes() == main_bytes
assert chapter_path.read_bytes() == chapter_bytes
restored = merged.replace(setup, '', 1)
new_start = restored.index(r'\section{问题四的分析与求解}')
new_end = restored.index(r'\section{模型的评价}', new_start)
assert restored[new_start:new_end] == chapter_body
assert restored[:new_start] == indented[:start]
assert restored[new_end:] == indented[end:]

report = {
    'original_main_sha256': hashlib.sha256(main_bytes).hexdigest(),
    'original_chapter_sha256': hashlib.sha256(chapter_bytes).hexdigest(),
    'integrated_main_sha256': hashlib.sha256(output_tex.read_bytes()).hexdigest(),
    'removed_noindent_count': len(removed),
    'removed_noindent_original_lines': removed,
    'retained_noindent_original_lines': [1065, 2512],
    'paragraph_formatting_addition': setup,
    'chapter_body_exact_match': True,
    'other_source_exact_match_after_authorized_indent_changes': True,
    'asset_count': len(copied),
    'assets': copied,
    'cross_reference_labels': len(labels),
    'undefined_cross_references': [],
}
(audit_dir / 'content_preservation_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(out_dir / '编译说明.txt').write_text(
    '整合稿主文件：MathModel.tex\n'
    '编译方式：在本文件夹内使用 XeLaTeX 编译 MathModel.tex；首次编译后再编译两次，以更新目录和交叉引用。\n'
    '本文件夹已收齐模板类文件及正文、封面、目录实际使用的图形资源，可独立编译。\n'
    '整合范围：以完整第七章替换旧占位内容；恢复中文正文首行缩进，包括列表条目内另起的正文段落。\n'
    '保留两处“当……公式……时”的同句续文不缩进。其余原文、公式、图表内容以及后续章节均保留。\n'
    '原2026建模比赛文件夹中的两个源文件均未改动。\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k not in ('assets', 'removed_noindent_original_lines')}, ensure_ascii=False, indent=2))
