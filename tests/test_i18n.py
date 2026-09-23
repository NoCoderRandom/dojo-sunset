"""Language detection, catalog completeness and invariant karate terms."""
import json
import tempfile
import unittest
from pathlib import Path

from dojo.i18n import LOCALES, Translator, available_languages, detect_language
from dojo.model import MOVES
from dojo.storage import Storage


class TranslationTests(unittest.TestCase):
    def catalogs(self):
        return {path.stem: json.loads(path.read_text(encoding='utf-8'))['strings']
                for path in LOCALES.glob('*.json')}

    def test_catalogs_have_identical_stable_keys(self):
        catalogs = self.catalogs()
        self.assertEqual(set(catalogs), {'sv', 'en'})
        self.assertEqual(set(catalogs['sv']), set(catalogs['en']))

    def test_swedish_keyboard_wins_over_english_system_locale(self):
        with tempfile.TemporaryDirectory() as temporary:
            keyboard = Path(temporary) / 'keyboard'
            keyboard.write_text('XKBLAYOUT="se"\n', encoding='utf-8')
            self.assertEqual(detect_language({'LANG': 'en_US.UTF-8'}, [keyboard]), 'sv')

    def test_english_keyboard_wins_over_swedish_system_locale(self):
        with tempfile.TemporaryDirectory() as temporary:
            keyboard = Path(temporary) / 'keyboard'
            keyboard.write_text('XKB_DEFAULT_LAYOUT=us\n', encoding='utf-8')
            self.assertEqual(detect_language({'LANG': 'sv_SE.UTF-8'}, [keyboard]), 'en')

    def test_locale_is_fallback_when_keyboard_is_unknown(self):
        self.assertEqual(detect_language({'LANG': 'sv_SE.UTF-8'}, []), 'sv')
        self.assertEqual(detect_language({'LANG': 'en_GB.UTF-8'}, []), 'en')

    def test_manual_language_overrides_detection(self):
        translator = Translator('en', {'XKB_DEFAULT_LAYOUT': 'se'}, [])
        self.assertEqual(translator('Spela match'), 'Play match')
        translator = Translator('sv', {'XKB_DEFAULT_LAYOUT': 'us'}, [])
        self.assertEqual(translator('Spela match'), 'Spela match')

    def test_dynamic_match_text_is_translated(self):
        translator = Translator('en')
        self.assertEqual(translator('KAGE VINNER RONDEN'), 'KAGE WINS THE ROUND')
        self.assertEqual(translator('NINJA • 3 KASTSTJÄRNOR'), 'NINJA • 3 THROWING STARS')
        self.assertEqual(translator('VITT BÄLTE'), 'WHITE BELT')

    def test_japanese_technique_names_never_change(self):
        translator = Translator('en')
        for key in ('jab', 'cross', 'front_kick', 'round_kick', 'high_kick',
                    'low_kick', 'sweep', 'jump_kick'):
            title = MOVES[key].title
            self.assertEqual(translator(title), title)

    def test_speedlink_text_uses_full_button_names(self):
        catalogs = self.catalogs()
        swedish = '\n'.join(catalogs['sv'].values()).lower()
        for name in ('vänster liten', 'höger liten', 'vänster stor', 'höger stor'):
            self.assertIn(name, swedish)
        for catalog in catalogs.values():
            text = '\n'.join(catalog.values())
            for unclear in ('LV/LH', 'SV/SH', '+ SV', '+SH'):
                self.assertNotIn(unclear, text)

    def test_language_setting_is_saved_and_invalid_code_is_repaired(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Storage(temporary)
            storage.settings['language'] = 'en'
            self.assertTrue(storage.save_settings())
            self.assertEqual(Storage(temporary).settings['language'], 'en')
            storage.settings['language'] = 'not-installed'
            self.assertTrue(storage.save_settings())
            self.assertEqual(Storage(temporary).settings['language'], 'auto')

    def test_available_languages_come_from_files(self):
        self.assertEqual(set(available_languages()), {'sv', 'en'})


if __name__ == '__main__':
    unittest.main()
