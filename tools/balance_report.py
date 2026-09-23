"""Seeded rule/AI balance sampling, separate from real-time render benchmarks."""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dojo.competition import ClassicMatch
from dojo.model import Brain, Command, Match
from dojo.storage import ROOT


def simulate(rules, left_level, right_level, seed, hz=120):
    match = ClassicMatch(right_level, seed) if rules == 'classic' else Match(right_level, seed=seed)
    brain = Brain(left_level, seed + 100000)
    attacks = Counter()
    hits = Counter()
    last_attacks = match.player.attacks
    last_hits = match.player.hits
    elapsed = 0.0
    while elapsed < 300:
        dt = 1 / hz
        # Match advances its own brain only during live, non-hit-stop frames.
        # Mirror that clock for the left AI; otherwise intros/point pauses
        # give the two opponents different reaction schedules.
        old_phase = match.phase
        command = (brain.update(dt, match.player, match.enemy)
                   if match.phase == 'fight' and match.hit_stop <= 0 else Command())
        match.update(dt, command)
        if old_phase == 'point' and match.phase == 'intro':
            brain.wait = .3
            brain.intent = Command()
        if match.player.attacks != last_attacks:
            attacks[command.attack or match.player.move_key] += 1
            last_attacks = match.player.attacks
        if match.player.hits != last_hits:
            hits[match.player.move_key] += 1
            last_hits = match.player.hits
        elapsed += dt
        if match.phase == 'finished':
            break
    return {
        'won': match.winner is match.player,
        'finished': match.phase == 'finished',
        'elapsed': round(elapsed, 2),
        'attacks': dict(attacks),
        'hits': dict(hits),
        'left_score': match.player.score,
        'right_score': match.enemy.score,
        'left_rounds': match.player.wins,
        'right_rounds': match.enemy.wins,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-pair', type=int, default=60)
    parser.add_argument('--label', default='balance')
    parser.add_argument('--hz', type=int, default=120)
    args = parser.parse_args()
    if args.hz <= 0 or args.per_pair <= 0:
        parser.error('hz and per-pair must be positive')
    report = []
    started = time.monotonic()
    source_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                     for name in ('dojo/model.py', 'dojo/competition.py', 'tools/balance_report.py')}
    for rules in ('classic', 'duel'):
        for left in range(3):
            for right in range(3):
                results = [simulate(rules, left, right, seed, args.hz) for seed in range(args.per_pair)]
                attacks = Counter()
                hits = Counter()
                for row in results:
                    attacks.update(row['attacks'])
                    hits.update(row['hits'])
                row = {
                    'rules': rules,
                    'left_difficulty': left,
                    'right_difficulty': right,
                    'matches': len(results),
                    'left_wins': sum(result['won'] for result in results),
                    'unfinished': sum(not result['finished'] for result in results),
                    'mean_simulated_seconds': round(sum(result['elapsed'] for result in results) / len(results), 2),
                    'attacks': dict(attacks),
                    'hits': dict(hits),
                }
                report.append(row)
                print(json.dumps(row), flush=True)
    output = {
        'wall_seconds': round(time.monotonic() - started, 2),
        'simulation_hz': args.hz,
        'source_hashes': source_hashes,
        'pairs': report,
    }
    (ROOT / 'userdata' / (args.label + '.json')).write_text(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
