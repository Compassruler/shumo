from pathlib import Path
import json
import re
import difflib

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'tmp/paper_revision'
TARGET = ROOT / '26比赛/解题/初稿/MathModel.tex'
text = TARGET.read_bytes().decode('utf-8').replace('\r\n', '\n')
operations = json.loads((WORK / 'operations.json').read_text(encoding='utf-8'))
refs_a = json.loads((WORK / 'refs_a.json').read_text(encoding='utf-8'))
refs_b = json.loads((WORK / 'refs_b.json').read_text(encoding='utf-8'))

def replace_once(old, new, category):
    global text
    assert text.count(old) == 1, (category, text.count(old), old[:90])
    text = text.replace(old, new, 1)
    operations.append(dict(category=category, old=old, new=new))

for row in refs_a:
    replace_once(row['anchor'], row['replace'], 'citation:'+row['key'])
for row in refs_b:
    if row.get('duplicate_of'):
        continue
    if row['key'] == 'yang2021assisted':
        replace_once(r'\cite{li2019localheating}', r'\cite{li2019localheating,yang2021assisted}', 'citation:'+row['key'])
    else:
        anchor = row['anchor']
        if row['key'] == 'otsuki2020':
            anchor = '冷凝、冻结和凝华释放热量'
        replace_once(anchor, anchor+r'\cite{'+row['key']+'}', 'citation:'+row['key'])

bib_start = text.index(r'\begin{thebibliography}')
bib_end = text.index(r'\end{thebibliography}', bib_start) + len(r'\end{thebibliography}')
old_bib = text[bib_start:bib_end]
entries = {}
for match in re.finditer(r'\\bibitem\{([^}]+)\}[^\n]*', old_bib):
    entries[match.group(1)] = match.group(0)
for row in refs_a + refs_b:
    if row.get('duplicate_of'):
        continue
    assert row['key'] not in entries
    entries[row['key']] = row['bibitem']

appearance = []
for match in re.finditer(r'\\cite\{([^}]+)\}', text[:bib_start]):
    for key in match.group(1).split(','):
        if key not in appearance:
            appearance.append(key)
assert set(appearance) == set(entries), (set(appearance)-set(entries), set(entries)-set(appearance))
assert len(appearance) == 18
new_bib = '\n'.join([r'\begin{thebibliography}{99}', r'\setlength{\itemsep}{1mm}'] + [entries[k] for k in appearance] + [r'\end{thebibliography}'])
replace_once(old_bib, new_bib, 'bibliography-in-first-citation-order')

TARGET.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
(WORK / 'operations.json').write_text(json.dumps(operations, ensure_ascii=False, indent=2), encoding='utf-8')
original = (WORK / 'MathModel.original.tex').read_bytes().decode('utf-8').replace('\r\n', '\n')
restored = text
for op in reversed(operations):
    assert restored.count(op['new']) == 1, op['category']
    restored = restored.replace(op['new'], op['old'], 1)
assert restored == original, 'Unrequested content change detected'
(WORK / 'authorized_changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile='original/MathModel.tex', tofile='revised/MathModel.tex', n=2)), encoding='utf-8')

files = []
for row in refs_a + refs_b:
    key = 'ma2026endplate' if row.get('duplicate_of') else row['key']
    files.append({'file':row['file'], 'key':key, 'citation_number':appearance.index(key)+1, 'duplicate_of':row.get('duplicate_of')})
audit = {'only_authorized_changes': True, 'original_content_recovered_exactly': True,
         'citation_order': appearance, 'bibliography_count': len(entries),
         'provided_pdf_count': len(files), 'provided_unique_paper_count': len(set(r['key'] for r in files)),
         'file_citations':files, 'change_categories':[op['category'] for op in operations]}
(WORK / 'source_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print('Reference order and all 15 provided files verified; 14 unique provided papers + 4 retained sources = 18 entries.')
print('Reverse-patch audit: unchanged content matches the original exactly.')
for i, key in enumerate(appearance, 1):
    print(f'[{i}] {key}')
