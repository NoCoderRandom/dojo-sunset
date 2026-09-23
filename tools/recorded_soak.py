"""Run the GPU soak as a child and retain its actual process exit status.

Useful for detached overnight runs: a report written before shutdown alone
cannot prove that controller, audio and OpenGL cleanup also completed.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=7200)
    parser.add_argument('--label', required=True)
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--specialists', action='store_true')
    args = parser.parse_args()
    if Path(args.label).name != args.label or args.label in ('.', '..'):
        parser.error('label must be a directory name, not a path')
    output = ROOT / 'userdata' / args.label
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / 'tools' / 'soak.py'),
               '--seconds', str(args.seconds), '--label', args.label]
    if args.windowed:
        command.append('--windowed')
    if args.specialists:
        command.append('--specialists')
    started = time.time()
    with (output / 'process.log').open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status = {'wrapper_pid': os.getpid(), 'child_pid': process.pid,
                  'started_utc_epoch': started, 'command': command, 'finished': False}
        (output / 'process.json').write_text(json.dumps(status, indent=2))

        def stop(signum, frame):
            if process.poll() is None:
                process.send_signal(signum)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        status['exit_code'] = process.wait()
        status['finished'] = True
        status['wall_seconds'] = round(time.time() - started, 2)
        temporary = output / 'process.json.tmp'
        temporary.write_text(json.dumps(status, indent=2))
        temporary.replace(output / 'process.json')
    return status['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
