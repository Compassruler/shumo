"""问题四单图入口：沿用前三问的预览、只导出及只预览选项。"""
from pathlib import Path
import argparse
import sys

def run_single(number, description):
    parser=argparse.ArgumentParser(description=description)
    parser.add_argument("--no-show", action="store_true", help="只导出，不打开交互窗口。")
    parser.add_argument("--no-save", action="store_true", help="只预览，不覆盖图和清单。")
    args=parser.parse_args()
    if not args.no_show:
        sys.argv.append("--show")
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from plot_results import main
    main(figure=number, no_show=args.no_show, no_save=args.no_save)
