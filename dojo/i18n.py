"""File-backed translations and safe keyboard-layout language detection."""
import json
import os
import re
from pathlib import Path

LOCALES = Path(__file__).with_name('locales')
DEFAULT_LANGUAGE = 'sv'


def available_languages():
    """Return installed language metadata without hard-coding language codes."""
    result = {}
    for path in sorted(LOCALES.glob('*.json')):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            meta = payload['meta']
            strings = payload['strings']
            if isinstance(meta['name'], str) and isinstance(strings, dict):
                result[path.stem] = meta
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return result


def _layout_from_text(text):
    match = re.search(r'(?im)^\s*(?:XKBLAYOUT|XKB_DEFAULT_LAYOUT)\s*=\s*["\']?([^"\'\n]+)', text)
    if not match:
        return ''
    return match.group(1).split(',')[0].strip().lower()


def detect_language(environ=None, paths=None):
    """Prefer keyboard layout, then OS locale; unknown systems use English."""
    environ = os.environ if environ is None else environ
    layout = environ.get('XKB_DEFAULT_LAYOUT', '').split(',')[0].strip().lower()
    if paths is None:
        paths = (Path.home() / '.config/labwc/environment', Path('/etc/default/keyboard'))
    if not layout:
        for path in paths:
            try:
                layout = _layout_from_text(Path(path).read_text(encoding='utf-8'))
            except OSError:
                continue
            if layout:
                break
    if layout in {'se', 'sv'}:
        return 'sv'
    if layout in {'us', 'gb', 'uk', 'en'}:
        return 'en'
    locale = next((environ.get(key, '') for key in ('LC_ALL', 'LC_MESSAGES', 'LANGUAGE', 'LANG')
                   if environ.get(key)), '')
    return 'sv' if locale.lower().startswith('sv') else 'en'


class Translator:
    """Resolve stable IDs, while accepting Swedish source text during migration."""

    def __init__(self, preference='auto', environ=None, paths=None):
        self.catalogs = {}
        self.meta = available_languages()
        for code in self.meta:
            payload = json.loads((LOCALES / f'{code}.json').read_text(encoding='utf-8'))
            self.catalogs[code] = payload['strings']
        self.source = self.catalogs[DEFAULT_LANGUAGE]
        self.reverse_source = {value: key for key, value in self.source.items()}
        detected = detect_language(environ, paths)
        self.preference = preference if preference == 'auto' or preference in self.catalogs else 'auto'
        self.language = detected if self.preference == 'auto' else self.preference
        if self.language not in self.catalogs:
            self.language = 'en' if 'en' in self.catalogs else DEFAULT_LANGUAGE

    def set_preference(self, preference):
        replacement = Translator(preference)
        self.__dict__.update(replacement.__dict__)

    def __call__(self, value, **fields):
        key = value if value in self.source else self.reverse_source.get(value)
        if not key:
            key, detected_fields = self._dynamic(value)
            fields = detected_fields | fields
        translated = self.catalogs[self.language].get(key, self.source.get(key, value)) if key else value
        localized_fields = {name: self(field) if isinstance(field, str) else field
                            for name, field in fields.items()}
        return translated.format(**localized_fields) if fields else translated

    def _dynamic(self, value):
        patterns = (
            (r'^(?P<name>.+) VINNER RONDEN$', 'match.round_winner'),
            (r'^(?P<name>.+) VINNER!$', 'match.winner'),
            (r'^ROND (?P<number>\d+)$', 'match.round'),
            (r'^(?P<count>\d+) TRÄFFAR I FÖLJD$', 'match.combo'),
            (r'^NINJA • (?P<count>\d+) KASTSTJÄRNOR$', 'hud.ninja_stars'),
            (r'^KARATE MOT (?P<opponent>.+)$', 'match.versus'),
            (r'^(?P<name>.+) BÄLTE$', 'journey.belt'),
            (r'^Spelare (?P<number>[12]): (?P<name>.*)$', 'controls.player_name'),
            (r'^(?P<prefix>AI|BACK): (?P<mode>.+)$', 'hud.ai_mode'),
            (r'^Kunde inte spara: (?P<error>.*)$', 'storage.save_error'),
            (r'^PERSONBÄSTA\s+(?P<score>\d+)$', 'title.best_score'),
            (r'^← / →\s+Byt sida\s+(?P<page>\d+) / 3$', 'footer.page_number'),
        )
        for pattern, key in patterns:
            match = re.match(pattern, value)
            if match:
                return key, match.groupdict()
        return None, {}

    def language_label(self, preference):
        if preference == 'auto':
            detected_name = self(f'language.name.{self.language}')
            return self('language.auto_value', language=detected_name)
        return self(f'language.name.{preference}')
