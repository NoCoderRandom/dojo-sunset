"""Independent-seed difficulty matrix for the new opponents.

All nine player/enemy difficulty pairings, with and without explicit counters.
Uses the same finite reaction clocks as specialist_balance, never perfect input.
"""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dojo.storage import ROOT
from tools.specialist_balance import simulate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-pair', type=int, default=50)
    parser.add_argument('--label', default='specialist-matrix')
    args = parser.parse_args()
    if args.per_pair < 1 or Path(args.label).name != args.label:
        parser.error('positive per-pair and a plain label required')
    started = time.monotonic()
    rows = []
    names = ('dojo/model.py', 'dojo/competition.py', 'tools/specialist_balance.py',
             'tools/specialist_matrix.py')
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    for kind in ('ninja', 'sumo'):
        for aware in (False, True):
            for player_level in range(3):
                for enemy_level in range(3):
                    outcomes = [simulate(kind, player_level, enemy_level, seed + 1000, aware)
                                for seed in range(args.per_pair)]
                    sounds, attacks = Counter(), Counter()
                    for outcome in outcomes:
                        sounds.update(outcome['events'])
                        attacks.update(outcome['enemy_attacks'])
                    row = {
                        'opponent': kind, 'player_level': player_level, 'enemy_level': enemy_level,
                        'aware_defense': aware, 'matches': len(outcomes),
                        'player_wins': sum(r['won'] for r in outcomes),
                        'unfinished': sum(not r['finished'] for r in outcomes),
                        'mean_seconds': round(sum(r['seconds'] for r in outcomes) / len(outcomes), 2),
                        'max_seconds': round(max(r['seconds'] for r in outcomes), 2),
                        'events': dict(sounds), 'enemy_attacks': dict(attacks),
                        'max_projectiles': max(r['max_projectiles'] for r in outcomes),
                    }
                    rows.append(row)
                    print(json.dumps(row), flush=True)
                    report = {'wall_seconds': round(time.monotonic() - started, 2),
                              'complete': len(rows) == 36, 'source_hashes': hashes,
                              'seed_start': 1000, 'per_pair': args.per_pair,
                              'simulation_hz': 120, 'pairs': rows}
                    (ROOT / 'userdata' / (args.label + '.json')).write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
