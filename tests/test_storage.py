"""Persistence must be safe, bounded, and independent of RetroArch."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dojo.model import Match
from dojo.storage import DEFAULTS, Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_files_have_defaults(self):
        storage = Storage(self.path)
        self.assertEqual(storage.settings, DEFAULTS)
        self.assertEqual(storage.records, [])

    def test_corrupt_json_does_not_crash(self):
        (self.path / 'settings.json').write_text('not json')
        (self.path / 'records.json').write_text('{bad')
        storage = Storage(self.path)
        self.assertEqual(storage.settings, DEFAULTS)
        self.assertEqual(storage.records, [])

    def test_clamps_out_of_range_settings(self):
        (self.path / 'settings.json').write_text(json.dumps({
            'difficulty': 999,
            'volume': -10.0,
            'deadzone': 50.0,
            'quality': -1,
            'arena': 20,
        }))
        storage = Storage(self.path)
        self.assertEqual(storage.settings['difficulty'], 2)
        self.assertEqual(storage.settings['volume'], 0)
        self.assertEqual(storage.settings['deadzone'], .4)
        self.assertEqual(storage.settings['quality'], 0)
        self.assertEqual(storage.settings['arena'], 1)

    def test_settings_roundtrip(self):
        storage = Storage(self.path)
        storage.settings['volume'] = .35
        storage.settings['rumble'] = False
        self.assertTrue(storage.save_settings())
        restored = Storage(self.path)
        self.assertEqual(restored.settings['volume'], .35)
        self.assertFalse(restored.settings['rumble'])
        self.assertFalse((self.path / 'settings.tmp').exists())

    def test_top_ten_records_sorted(self):
        storage = Storage(self.path)
        for score in range(15):
            match = Match(seed=1)
            match.player.score = score * 100
            match.winner = match.player
            self.assertTrue(storage.add_record(match))
        restored = Storage(self.path)
        self.assertEqual(len(restored.records), 10)
        self.assertEqual(restored.best_score, 1400)
        self.assertEqual(restored.records[-1]['score'], 500)

    def test_no_files_outside_requested_directory(self):
        storage = Storage(self.path / 'isolated')
        storage.save_settings()
        storage.add_record(Match(seed=1))
        self.assertEqual(sorted(p.name for p in self.path.iterdir()), ['isolated'])

    def test_last_good_backup_recovers_a_truncated_save(self):
        storage = Storage(self.path)
        storage.settings['volume'] = .25
        storage.save_settings()
        storage.settings['volume'] = .75
        storage.save_settings()
        (self.path / 'settings.json').write_text('{truncated')
        restored = Storage(self.path)
        self.assertEqual(restored.settings['volume'], .25)

    def test_failed_replace_does_not_destroy_previous_settings(self):
        storage = Storage(self.path)
        storage.settings['volume'] = .25
        storage.save_settings()
        original = (self.path / 'settings.json').read_bytes()
        storage.settings['volume'] = .75
        with patch('dojo.storage.os.replace', side_effect=OSError('disk full')):
            self.assertFalse(storage.save_settings())
        self.assertEqual((self.path / 'settings.json').read_bytes(), original)
        self.assertIn('disk full', storage.error)
        self.assertEqual(list(self.path.glob('*.tmp')), [])

    def test_practice_cannot_enter_record_table(self):
        storage = Storage(self.path)
        match = Match(practice=True)
        match.player.score = 999999
        self.assertFalse(storage.add_record(match))
        self.assertEqual(storage.records, [])

    def test_malformed_record_metadata_is_sanitized(self):
        (self.path / 'records.json').write_text(json.dumps([
            {'name': 'BRUCE PI', 'score': 100, 'difficulty': 'bad'},
            {'name': 'BAD', 'score': -1},
            {'name': 'BAD', 'score': True},
        ]))
        storage = Storage(self.path)
        self.assertEqual(len(storage.records), 1)
        self.assertEqual(storage.records[0]['difficulty'], 1)

    def test_invalid_utf8_can_be_replaced_without_losing_good_backup(self):
        storage = Storage(self.path)
        storage.settings['volume'] = .25
        storage.save_settings()
        storage.settings['volume'] = .5
        storage.save_settings()
        (self.path / 'settings.json').write_bytes(b'\xff\xfeinvalid')
        restored = Storage(self.path)
        self.assertEqual(restored.settings['volume'], .25)
        restored.settings['volume'] = .75
        self.assertTrue(restored.save_settings())
        self.assertEqual(Storage(self.path).settings['volume'], .75)
        backup = json.loads((self.path / 'settings.json.bak').read_text())
        self.assertEqual(backup['volume'], .25)

    def test_nonfinite_numbers_use_defaults(self):
        (self.path / 'settings.json').write_text(
            '{"volume": NaN, "deadzone": Infinity}')
        storage = Storage(self.path)
        self.assertEqual(storage.settings['volume'], DEFAULTS['volume'])
        self.assertEqual(storage.settings['deadzone'], DEFAULTS['deadzone'])

    def test_wrong_json_shapes_are_ignored(self):
        (self.path / 'settings.json').write_text('[1,2,3]')
        (self.path / 'records.json').write_text('{"score":1}')
        storage = Storage(self.path)
        self.assertEqual(storage.settings, DEFAULTS)
        self.assertEqual(storage.records, [])


if __name__ == '__main__':
    unittest.main()
