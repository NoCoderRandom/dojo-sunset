"""Seeded karate-versus-specialist matches with finite reaction-time counters.

This is a balance probe, not a claim that an AI predicts human enjoyment.
The optional aware policy tests whether the advertised defenses are useful.
"""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dojo.competition import opponent_match
from dojo.model import Brain, Command
from dojo.storage import ROOT


def player_command(brain, match, dt, aware=True):
    if match.phase != 'fight' or match.hit_stop > 0:
        return Command()
    decision = brain.wait <= dt
    command = brain.update(dt, match.player, match.enemy)
    if aware and decision:
        enemy = match.enemy
        distance = abs(enemy.x - match.player.x)
        incoming = any((match.player.x - star.x) * star.velocity > 0
                       and abs(match.player.x - star.x) < 2.4 for star in match.projectiles)
        if incoming or enemy.attacking and enemy.move_key == 'nunchaku' and distance < 2.1:
            command = Command(crouch=True)
        elif (enemy.attacking and enemy.move_key == 'sumo_stomp' and distance < 1.6
              and enemy.elapsed > .15 and enemy.elapsed < enemy.move.startup):
            command = Command(jump=True)
        elif enemy.attacking and enemy.move_key == 'sumo_charge' and distance < 2.1:
            command = Command(move=-match.player.facing)
        brain.intent = command
    return command


def simulate(kind, left, right, seed, aware):
    match = opponent_match(kind, right, seed=seed)
    brain = Brain(left, seed + 50000)
    events = Counter()
    attacks = Counter()
    previous_attacks = 0
    elapsed = 0
    max_projectiles = 0
    while elapsed < 300:
        dt = 1 / 120
        command = player_command(brain, match, dt, aware)
        match.update(dt, command)
        elapsed += dt
        events.update(match.events)
        if match.enemy.attacks != previous_attacks:
            attacks[match.enemy.move_key] += 1
            previous_attacks = match.enemy.attacks
        max_projectiles = max(max_projectiles, len(match.projectiles))
        for fighter in (match.player, match.enemy):
            assert -4.501 <= fighter.x <= 4.501
            assert 0 <= fighter.health <= 100
            assert 0 <= fighter.stamina <= 100.001
            assert 0 <= fighter.stars <= 4
        assert len(match.projectiles) <= 4
        if match.phase in ('intro', 'round_over', 'finished'):
            assert not match.projectiles
        if match.phase == 'finished':
            break
    return {'won': match.winner is match.player, 'finished': match.phase == 'finished',
            'seconds': elapsed, 'events': dict(events), 'enemy_attacks': dict(attacks),
            'max_projectiles': max_projectiles}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-pair', type=int, default=20)
    parser.add_argument('--label', default='specialist-balance')
    args = parser.parse_args()
    if args.per_pair < 1 or Path(args.label).name != args.label:
        parser.error('positive per-pair and a plain label required')
    started = time.monotonic()
    pairs = []
    hashes = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
              for f in ('dojo/model.py', 'dojo/competition.py', 'tools/specialist_balance.py')}
    for kind in ('ninja', 'sumo'):
        for aware in (False, True):
            for level in range(3):
                matches = [simulate(kind, level, level, seed, aware) for seed in range(args.per_pair)]
                events = Counter()
                attacks = Counter()
                for result in matches:
                    events.update(result['events'])
                    attacks.update(result['enemy_attacks'])
                row = {'opponent': kind, 'difficulty': level, 'aware_defense': aware,
                       'matches': len(matches), 'player_wins': sum(r['won'] for r in matches),
                       'unfinished': sum(not r['finished'] for r in matches),
                       'mean_seconds': round(sum(r['seconds'] for r in matches) / len(matches), 2),
                       'events': dict(events), 'enemy_attacks': dict(attacks),
                       'max_projectiles': max(r['max_projectiles'] for r in matches)}
                pairs.append(row)
                print(json.dumps(row), flush=True)
    report = {'wall_seconds': round(time.monotonic() - started, 2), 'simulation_hz': 120,
              'source_hashes': hashes, 'pairs': pairs}
    (ROOT / 'userdata' / (args.label + '.json')).write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
