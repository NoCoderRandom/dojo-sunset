#!/usr/bin/env python3
"""One-click, single-instance startup with local logs and a readable error box."""
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'userdata'


def show_error(message):
    if shutil.which('zenity'):
        subprocess.run(['zenity', '--error', '--title=Dojo Sunset', '--text=' + message], check=False)
    elif shutil.which('xmessage'):
        subprocess.run(['xmessage', '-center', message], check=False)
    else:
        print(message, file=sys.stderr)


def main():
    os.chdir(ROOT)
    DATA.mkdir(exist_ok=True)
    lock = (DATA / 'game.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        show_error('Dojo Sunset körs redan. Växla till spelfönstret med Alt+Tab.')
        return 0
    log = DATA / 'game.log'
    if log.exists() and log.stat().st_size > 512_000:
        log.replace(DATA / 'game-previous.log')
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    with log.open('a', buffering=1) as output:
        process = subprocess.run([sys.executable, str(ROOT / 'main.py'), *sys.argv[1:]],
                                 cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    if process.returncode:
        show_error('Spelet kunde inte starta eller stängdes oväntat.\n'
                   'Detaljer finns i Dojo Sunset/userdata/game.log.\n'
                   'Din retroinstallation har inte ändrats.')
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
