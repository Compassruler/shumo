"""Compatibility entry point for canonical Q3 publication figures.

Uses the current per-figure Python scripts to prevent stale duplicate layouts
or ice-metric labels from being reintroduced. Reads saved CSVs only.
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys

DEFAULT_ROOT=Path(__file__).resolve().parents[2]/"解题"/"问题3_求解结果"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=DEFAULT_ROOT)
    args=parser.parse_args()
    scripts=args.root/"code"/"figure_scripts"
    env=os.environ.copy()
    env.setdefault("MPLBACKEND","Agg")
    for script in sorted(scripts.glob("fig[0-9][0-9]_*.py")):
        subprocess.run([sys.executable,str(script),"--no-show"],check=True,env=env)

if __name__=="__main__":
    main()
