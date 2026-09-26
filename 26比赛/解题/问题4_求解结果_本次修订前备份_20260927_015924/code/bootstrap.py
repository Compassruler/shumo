"""Use an optional portable dependency directory; normal pip environments also work."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / '.python_deps'
if DEPS.is_dir():
    sys.path.insert(0, str(DEPS))
