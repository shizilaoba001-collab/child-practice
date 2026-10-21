#!/usr/bin/env python3
"""Install into this checkout's .venv; never install globally or start a background service."""
import os
from pathlib import Path
import subprocess
import sys
import venv

root=Path(__file__).resolve().parent
if sys.version_info<(3,9):
    raise SystemExit('需要Python 3.9或以上')
env=root/'.venv'
if not env.exists():
    venv.EnvBuilder(with_pip=True).create(env)
python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.is_file():
    raise SystemExit('既有.venv不完整，请检查该目录；本脚本不删除它')
skill=root/'.agents/skills/child-practice'
subprocess.run([str(python),'-m','pip','install','-r',str(skill/'requirements.txt')],check=True)
subprocess.run([str(python),str(skill/'scripts/practice.py'),'doctor'],check=True)
print((skill/'references/welcome.md').read_text(encoding='utf-8'))
