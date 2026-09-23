"""Exercise native cleanup and prove the soak observer does not retain the app.

Each case runs in a separate process with private saves and SDL-only pads.
Transitions are deliberately forced; these are lifecycle checks, not wins.
"""
import argparse
import faulthandler
import gc
import json
import subprocess
import sys
import time
import weakref
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def child(label, windowed, transitions):
    import pygame
    from OpenGL.GL import glFinish, glGetError

    from tools.sdl_virtual import VirtualPad
    from tools.soak import Soak

    faulthandler.enable()
    soak = Soak(0, label, not windowed, True)
    output = soak.out
    temporary = Path(soak.temp.name)
    # Actual GL drawing, without waiting for a powered-off desktop to present.
    soak.app.renderer.present = lambda: None
    reconnects = 0
    for index in range(max(1, transitions)):
        kind = ('karate', 'ninja', 'sumo')[index % 3]
        soak.app.new_match(False, kind)
        if index and index % 3 == 0:
            soak.app.storage.settings['arena'] = index % 2
            soak.app.renderer.change_arena()
        if index and index % 5 == 0:
            soak.app.controls.close_pad()
            soak.pad.close()
            soak.pad = VirtualPad()
            soak.app.controls.preferred_instance = soak.pad.instance_id
            soak.app.controls.scan()
            reconnects += 1
        soak.app.controls.poll(.016)
        soak.app.audio.play('menu')
        soak.app.draw(.016)
        glFinish()
        assert glGetError() == 0
    assert soak.sound_events['menu'] == max(1, transitions)
    app_ref = weakref.ref(soak.app)
    audio_ref = weakref.ref(soak.app.audio)
    observed_events = dict(soak.sound_events)
    gc.disable()
    soak.close()
    del soak
    released = app_ref() is None and audio_ref() is None
    assert released, 'Native-owning app/audio survived shutdown until cyclic GC'
    assert not temporary.exists(), 'Temporary saves survived shutdown'
    shutdown = json.loads((output / 'shutdown.json').read_text())
    assert shutdown['complete']
    assert not pygame.display.get_init()
    gc.enable()
    result = {'windowed': windowed, 'forced_transitions': transitions,
              'controller_reconnects': reconnects, 'released_without_gc': released,
              'temporary_data_removed': True, 'sound_events': observed_events,
              'shutdown': shutdown}
    (output / 'lifecycle.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--label', default='shutdown-lifecycle')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--transitions', type=int, default=0)
    args = parser.parse_args()
    if args.child:
        child(args.label, args.windowed, args.transitions)
        return 0
    output = ROOT / 'userdata' / args.label
    output.mkdir(parents=True, exist_ok=True)
    results = []
    started = time.monotonic()
    for index, (windowed, transitions) in enumerate(
            (w, n) for w in (False, True) for n in (0, 6, 30, 60)):
        label = f'{args.label}-{index}'
        command = [sys.executable, str(Path(__file__)), '--child', '--label', label,
                   '--transitions', str(transitions)]
        if windowed:
            command.append('--windowed')
        with (output / f'{index}.log').open('w') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log,
                                     stderr=subprocess.STDOUT, timeout=60)
        result = {'case': index, 'windowed': windowed,
                  'forced_transitions': transitions, 'exit_code': process.returncode}
        results.append(result)
        print(json.dumps(result), flush=True)
        report = {'cases': results, 'seconds': round(time.monotonic() - started, 2),
                  'complete': index == 7, 'all_passed': all(r['exit_code'] == 0 for r in results)}
        (output / 'report.json').write_text(json.dumps(report, indent=2))
        if process.returncode:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
