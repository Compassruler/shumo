"""Validate final local links, CSV deliverables, images and source provenance."""
import sys
if sys.platform=='win32':import bootstrap
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote
import hashlib
import xml.etree.ElementTree as ET
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
    figure_dir=ROOT/'figures'
    formats={ext:sorted(figure_dir.glob('*.'+ext)) for ext in ('pdf','svg','png')}
    add('17_pdf_17_svg_and_17_png',all(len(paths)==17 for paths in formats.values()),
        {ext:len(paths) for ext,paths in formats.items()})
    stems={ext:{path.stem for path in paths} for ext,paths in formats.items()}
    add('figure_format_stems_match',len(stems['png'])==17 and stems['pdf']==stems['svg']==stems['png'],
        {ext:sorted(names) for ext,names in stems.items()})
    manifest_path=figure_dir/'figure_manifest.csv'
    add('figure_manifest_exists',manifest_path.is_file(),manifest_path.name)
    if manifest_path.is_file():
        figures=pd.read_csv(manifest_path,encoding='utf-8-sig')
        required={'figure','png','svg','pdf','png_dpi'}
        add('figure_manifest_required_columns',required.issubset(figures.columns),list(figures.columns))
        add('figure_manifest_17_rows',len(figures)==17,len(figures))
        if required.issubset(figures.columns):
            names=figures['figure'].astype(str)
            add('figure_manifest_unique_and_complete',names.is_unique and set(names)==stems['png'],
                names.tolist())
            dpi=pd.to_numeric(figures['png_dpi'],errors='coerce')
            add('figure_manifest_png_300_dpi',dpi.sub(300).abs().le(.1).all(),dpi.tolist())
            for ext in formats:
                listed=figures[ext].astype(str)
                expected=names+'.'+ext
                add('figure_manifest_'+ext+'_files',
                    listed.eq(expected).all() and set(listed)=={path.name for path in formats[ext]}
                    and all((figure_dir/name).is_file() for name in listed),listed.tolist())
    for path in formats['png']:
        try:
            with Image.open(path) as image:
                add('image_readable_'+path.stem,min(image.size)>1000,str(image.size))
                dpi=image.info.get('dpi',())
                add('png_300_dpi_'+path.stem,len(dpi)==2 and all(abs(v-300)<.1 for v in dpi),dpi)
                image.verify()
        except (OSError,SyntaxError,ValueError) as error:
            add('image_readable_'+path.stem,False,error)
    for path in formats['svg']:
        try:
            svg=ET.parse(path).getroot()
            editable=any(''.join(node.itertext()).strip() for node in svg.iter()
                         if node.tag.rsplit('}',1)[-1]=='text')
            add('svg_editable_text_'+path.stem,
                svg.tag.rsplit('}',1)[-1]=='svg' and editable,'SVG with editable text' if editable else 'No text nodes')
        except (OSError,ET.ParseError) as error:
            add('svg_editable_text_'+path.stem,False,error)
    for path in formats['pdf']:
        content=path.read_bytes()
        add('pdf_container_valid_'+path.stem,
            content.startswith(b'%PDF-') and b'%%EOF' in content[-1024:],len(content))
    for name,count in [('main_results.csv',9),('constant_scan.csv',19),('guarded_results.csv',3),
                        ('robustness.csv',90),('guarded_robustness.csv',90),('coupled_convergence.csv',9),
                        ('optimized_constant_results.csv',3),('guarded_parameter_validation.csv',24),('guarded_convergence.csv',21),
                        ('constant_robustness.csv',180),('constant_parameter_validation.csv',48),('observer_example_results.csv',3),('independent_initialization_validation.csv',108),('guarded_training_recheck.csv',18),('structural_comparison.csv',36),('structural_initial_temperatures.csv',12),('dynamic_deadline_frontier.csv',12)]:
        df=pd.read_csv(ROOT/'data'/name);add('rows_'+name,len(df)==count,len(df))
    for name in ('independent_export_validation.csv','model_validation.csv','precooling_validation.csv','revision_validation.csv'):
        df=pd.read_csv(ROOT/'data'/name);add('checks_'+name,df.passed.all(),f'{df.passed.sum()}/{len(df)}')
    for name in ('guarded_robustness.csv','guarded_parameter_validation.csv','independent_initialization_validation.csv','guarded_training_recheck.csv','structural_comparison.csv','dynamic_deadline_frontier.csv'):
        current=pd.read_csv(ROOT/'data'/name)
        add('independent_prior_'+name,current.observer_initialization.eq('nominal_precooling_prior').all() and current.reference_initialization.eq('initial_temperature_measurement').all(),'Separated plant initial condition and measured reference')
        add('feasible_'+name,current.feasible.all(),f'{current.feasible.sum()}/{len(current)}')
    current=pd.read_csv(ROOT/'data/dynamic_deadline_frontier.csv')
    add('120s_excluded_from_main_budget',not current.loc[current.deadline_s>100,'within_main_budget'].any(),'120 s is an additional scenario')
    current=pd.read_csv(ROOT/'data/guarded_training_recheck.csv')
    add('frozen_training_time_reserve',current.training_reserve_passed.all(),f'{current.training_reserve_passed.sum()}/{len(current)}')
    summaries=pd.concat([pd.read_csv(ROOT/'data'/name) for name in
        ('main_results.csv','guarded_results.csv','optimized_constant_results.csv')])
    states=pd.read_csv(ROOT/'data/controller_state_duration.csv')
    duration=states.groupby(['case','strategy','cell'],as_index=False).duration_s.sum()
    duration=duration.merge(summaries[['case','strategy','stop_s']],on=['case','strategy'])
    error=(duration.duration_s-duration.stop_s).abs().max()
    add('state_durations_cover_startup',error<1e-7,error)
    off=states.loc[states.state==5,'duration_s'].abs().max()
    add('shutdown_state_has_zero_startup_duration',off<1e-9,off)
    constant=states[states.strategy.str.contains('constant')]
    nonzero=constant.loc[constant.state!=0,'duration_s'].abs().max()
    add('constant_startup_state_code_zero',nonzero<1e-9,nonzero)
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
