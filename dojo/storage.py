"""All writable game data lives next to the game, never in emulator folders."""
import json
import math
import os
import time
from pathlib import Path

from .i18n import available_languages

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'userdata'
DEFAULTS = {
    'difficulty': 1,
    'volume': .55,
    'fullscreen': True,
    'quality': 1,
    'rumble': True,
    'deadzone': .22,
    'arena': 0,
    'rules': 0,
    'controller_p1': 'auto',
    'controller_p2': 'auto',
    'language': 'auto',
}


class Storage:
    def __init__(self, directory=DATA):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.settings = dict(DEFAULTS)
        self.records = []
        self.error = ''
        self.load()

    def read_json(self, name, fallback):
        for path in (self.directory / name, self.directory / (name + '.bak')):
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError, TypeError):
                continue
        return fallback

    def load(self):
        raw = self.read_json('settings.json', {})
        if isinstance(raw, dict):
            for key, default in DEFAULTS.items():
                value = raw.get(key, default)
                if type(value) is type(default):
                    if isinstance(value, float) and not math.isfinite(value):
                        continue
                    self.settings[key] = value
        self.settings['difficulty'] = max(0, min(2, self.settings['difficulty']))
        self.settings['quality'] = max(0, min(1, self.settings['quality']))
        self.settings['volume'] = max(0.0, min(1.0, self.settings['volume']))
        self.settings['deadzone'] = max(.12, min(.4, self.settings['deadzone']))
        self.settings['rules'] = max(0, min(1, self.settings['rules']))
        self.settings['arena'] = max(0, min(1, self.settings['arena']))
        for key in ('controller_p1', 'controller_p2'):
            if self.settings[key] not in ('auto', 'xbox', 'speedlink'):
                self.settings[key] = 'auto'
        if self.settings['language'] != 'auto' and self.settings['language'] not in available_languages():
            self.settings['language'] = 'auto'
        raw = self.read_json('records.json', [])
        self.records = []
        if isinstance(raw, list):
            for record in raw:
                if not isinstance(record, dict):
                    continue
                if type(record.get('score')) is not int or not isinstance(record.get('name'), str):
                    continue
                if not 0 <= record['score'] <= 999999999:
                    continue
                clean = dict(record)
                clean['name'] = clean['name'][:18]
                difficulty = clean.get('difficulty', 1)
                clean['difficulty'] = max(0, min(2, difficulty)) if type(difficulty) is int else 1
                clean['date'] = str(clean.get('date', ''))[:10]
                self.records.append(clean)
            self.records.sort(key=lambda row: row['score'], reverse=True)
            self.records = self.records[:10]

    def atomic_write(self, target, payload):
        temporary = target.with_name(target.name + '.tmp')
        try:
            with temporary.open('w', encoding='utf-8') as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise

    def write_json(self, name, value):
        target = self.directory / name
        try:
            if target.exists():
                try:
                    previous = target.read_text(encoding='utf-8')
                    json.loads(previous)
                except ValueError:
                    pass
                else:
                    self.atomic_write(target.with_name(name + '.bak'), previous)
            payload = json.dumps(value, ensure_ascii=False, indent=2)
            self.atomic_write(target, payload)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            self.error = ''
            return True
        except OSError as exc:
            self.error = 'Kunde inte spara: ' + str(exc)
            return False

    def save_settings(self):
        return self.write_json('settings.json', self.settings)

    def add_record(self, match):
        if match.practice:
            return False
        fighter = match.player
        record = {
            'name': fighter.name,
            'score': fighter.score,
            'won': match.winner is fighter,
            'difficulty': match.brain.difficulty,
            'date': time.strftime('%Y-%m-%d'),
            'hits': fighter.hits,
            'attacks': fighter.attacks,
            'best_combo': fighter.best_combo,
            'rules': getattr(match, 'rules', 'duel'),
        }
        self.records.append(record)
        self.records.sort(key=lambda row: row['score'], reverse=True)
        self.records = self.records[:10]
        return self.write_json('records.json', self.records)

    @property
    def best_score(self):
        return max((record['score'] for record in self.records), default=0)
