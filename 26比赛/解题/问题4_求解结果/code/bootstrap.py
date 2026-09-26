"""Use portable wheels only when Python ABI, OS and CPU tags are compatible."""
from pathlib import Path
import os
import platform
import sys
ROOT = Path(__file__).resolve().parents[1]

def portable_compatible(directory):
    if sys.implementation.name != 'cpython':
        return False
    python_tag = f'cp{sys.version_info.major}{sys.version_info.minor}'
    machine = platform.machine().lower()
    platform_suffix = {'aarch64':'arm64','amd64':'amd64','x86_64':'x86_64'}.get(machine,machine)
    for package in ('numpy','numba','llvmlite'):
        wheels=list(directory.glob(package+'-*.dist-info/WHEEL'))
        if len(wheels)!=1:
            return False
        compatible=False
        for line in wheels[0].read_text().splitlines():
            if not line.startswith('Tag: '):
                continue
            py,abi,plat=line[5:].strip().split('-')
            if py!=python_tag or abi!=python_tag:
                continue
            if sys.platform=='darwin':
                valid_os=plat.startswith('macosx_') and (plat.endswith('_'+platform_suffix) or plat.endswith('_universal2'))
                if valid_os:
                    minimum=tuple(map(int,plat.split('_')[1:3]));current=tuple(map(int,platform.mac_ver()[0].split('.')[:2]));valid_os=current>=minimum
            elif os.name=='nt':
                arch='amd64' if machine in ('amd64','x86_64') else machine
                valid_os=plat=='win_'+arch
            else:
                # No Linux wheel directory is shipped with this project.
                valid_os=False
            compatible |= valid_os
        if not compatible:
            return False
    return True

DEPS = ROOT / '.python_deps' if os.name=='nt' else ROOT.parent / '问题2_求解结果' / '.python_deps'
if DEPS.is_dir() and portable_compatible(DEPS):
    sys.path.insert(0,str(DEPS))
