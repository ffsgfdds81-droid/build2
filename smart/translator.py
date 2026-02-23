import json
import os
import re
from typing import List, Dict, Optional, Callable

DATA_DIR = os.path.expanduser('~/.simple_browser')
TRANSLATOR_FILE = os.path.join(DATA_DIR, 'translator.json')


class Language:
    def __init__(self, code: str, name: str, native_name: str = ''):
        self.code = code
        self.name = name
        self.native_name = native_name or name


class TranslationResult:
    def __init__(self, original: str, translated: str, 
                 source_lang: str, target_lang: str):
        self.original = original
        self.translated = translated
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timestamp = None
    
    def to_dict(self) -> dict:
        return {
            'original': self.original,
            'translated': self.translated,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang
        }


class Translator:
    def __init__(self):
        self.source_lang = 'auto'
        self.target_lang = 'en'
        self.history: List[TranslationResult] = []
        self.favorites: List[TranslationResult] = []
        
        self._load_languages()
        self._load()
    
    def _load_languages(self):
        self.languages = {
            'auto': Language('auto', 'Auto Detect'),
            'en': Language('en', 'English', 'English'),
            'ru': Language('ru', 'Russian', 'Русский'),
            'uk': Language('uk', 'Ukrainian', 'Українська'),
            'be': Language('be', 'Belarusian', 'Беларуская'),
            'es': Language('es', 'Spanish', 'Español'),
            'fr': Language('fr', 'French', 'Français'),
            'de': Language('de', 'German', 'Deutsch'),
            'it': Language('it', 'Italian', 'Italiano'),
            'pt': Language('pt', 'Portuguese', 'Português'),
            'pl': Language('pl', 'Polish', 'Polski'),
            'tr': Language('tr', 'Turkish', 'Türkçe'),
            'zh': Language('zh', 'Chinese', '中文'),
            'ja': Language('ja', 'Japanese', '日本語'),
            'ko': Language('ko', 'Korean', '한국어'),
            'ar': Language('ar', 'Arabic', 'العربية'),
            'hi': Language('hi', 'Hindi', 'हिन्दी'),
            'th': Language('th', 'Thai', 'ไทย'),
            'vi': Language('vi', 'Vietnamese', 'Tiếng Việt'),
            'id': Language('id', 'Indonesian', 'Bahasa Indonesia'),
            'ms': Language('ms', 'Malaysian', 'Bahasa Melayu'),
            'nl': Language('nl', 'Dutch', 'Nederlands'),
            'sv': Language('sv', 'Swedish', 'Svenska'),
            'da': Language('da', 'Danish', 'Dansk'),
            'no': Language('no', 'Norwegian', 'Norsk'),
            'fi': Language('fi', 'Finnish', 'Suomi'),
            'el': Language('el', 'Greek', 'Ελληνικά'),
            'he': Language('he', 'Hebrew', 'עברית'),
            'cs': Language('cs', 'Czech', 'Čeština'),
            'sk': Language('sk', 'Slovak', 'Slovenčina'),
            'hu': Language('hu', 'Hungarian', 'Magyar'),
            'ro': Language('ro', 'Romanian', 'Română'),
            'bg': Language('bg', 'Bulgarian', 'Български'),
            'hr': Language('hr', 'Croatian', 'Hrvatski'),
            'sr': Language('sr', 'Serbian', 'Српски'),
            'sl': Language('sl', 'Slovenian', 'Slovenščina'),
            'lt': Language('lt', 'Lithuanian', 'Lietuvių'),
            'lv': Language('lv', 'Latvian', 'Latviešu'),
            'et': Language('et', 'Estonian', 'Eesti'),
        }
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(TRANSLATOR_FILE):
            try:
                with open(TRANSLATOR_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [
                        TranslationResult(
                            h['original'], h['translated'],
                            h['source_lang'], h['target_lang']
                        ) for h in data.get('history', [])
                    ]
                    self.favorites = [
                        TranslationResult(
                            f['original'], f['translated'],
                            f['source_lang'], f['target_lang']
                        ) for f in data.get('favorites', [])
                    ]
            except:
                pass
    
    def _save(self):
        data = {
            'history': [h.to_dict() for h in self.history[:50]],
            'favorites': [f.to_dict() for f in self.favorites]
        }
        with open(TRANSLATOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def translate(self, text: str, source: str = 'auto', 
                  target: str = None) -> TranslationResult:
        if not text:
            return None
        
        if target is None:
            target = self.target_lang
        
        translated = self._translate_text(text, source, target)
        
        result = TranslationResult(text, translated, source, target)
        
        self.history.insert(0, result)
        self.history = self.history[:100]
        
        self._save()
        
        return result
    
    def _translate_text(self, text: str, source: str, target: str) -> str:
        lang_names = {
            'en': 'English', 'ru': 'Russian', 'uk': 'Ukrainian',
            'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'zh': 'Chinese',
            'ja': 'Japanese', 'ko': 'Korean'
        }
        
        if source == 'auto':
            source = self._detect_language(text)
        
        if source == target:
            return text
        
        source_name = lang_names.get(source, source)
        target_name = lang_names.get(target, target)
        
        return f"[{target_name}] {text}"
    
    def _detect_language(self, text: str) -> str:
        cyrillic = re.findall(r'[\u0400-\u04FF]', text)
        if len(cyrillic) / len(text) > 0.3:
            if any(c in text for c in ['ій', 'є', 'ї']):
                return 'uk'
            return 'ru'
        
        cjk = re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text)
        if cjk:
            if any(ord(c) > 0x3000 for c in cjk):
                return 'zh'
            return 'ja'
        
        korean = re.findall(r'[\uac00-\ud7af]', text)
        if korean:
            return 'ko'
        
        return 'en'
    
    def detect_language(self, text: str) -> str:
        return self._detect_language(text)
    
    def get_languages(self) -> Dict[str, str]:
        return {code: lang.name for code, lang in self.languages.items()}
    
    def get_language_name(self, code: str) -> str:
        return self.languages.get(code, Language(code, code)).name
    
    def set_source_lang(self, lang: str):
        if lang in self.languages:
            self.source_lang = lang
    
    def set_target_lang(self, lang: str):
        if lang in self.languages:
            self.target_lang = lang
    
    def swap_languages(self):
        if self.source_lang != 'auto':
            self.source_lang, self.target_lang = self.target_lang, self.source_lang
    
    def get_history(self, limit: int = 20) -> List[TranslationResult]:
        return self.history[:limit]
    
    def get_favorites(self) -> List[TranslationResult]:
        return self.favorites
    
    def add_to_favorites(self, result: TranslationResult):
        for fav in self.favorites:
            if fav.original == result.original:
                return
        self.favorites.append(result)
        self._save()
    
    def remove_from_favorites(self, original: str) -> bool:
        initial_len = len(self.favorites)
        self.favorites = [f for f in self.favorites if f.original != original]
        if len(self.favorites) < initial_len:
            self._save()
            return True
        return False
    
    def clear_history(self):
        self.history = []
        self._save()
    
    def translate_page(self, html: str, source: str = 'auto', 
                       target: str = None) -> str:
        text = self.translate(html, source, target)
        if text:
            return f"<!-- Translated to {self.get_language_name(target)} -->\n{html}"
        return html


class Dictionary:
    def __init__(self):
        self.history: List[Dict] = []
    
    def define(self, word: str, lang: str = 'en') -> Optional[Dict]:
        if not word:
            return None
        
        word = word.lower().strip()
        
        definitions = {
            'en': {
                'browser': 'A software application for accessing information on the World Wide Web.',
                'search': 'The act of looking for something in a database or on the internet.',
                'bookmark': 'A saved link to a webpage for quick access.',
            },
            'ru': {
                'браузер': 'Программное обеспечение для просмотра веб-страниц.',
                'поиск': 'Процесс нахождения информации.',
                'закладка': 'Сохранённая ссылка на веб-страницу.',
            }
        }
        
        lang_defs = definitions.get(lang, {})
        
        result = {
            'word': word,
            'language': lang,
            'definition': lang_defs.get(word, f'Definition for "{word}" not found.'),
            'examples': [],
            'synonyms': []
        }
        
        self.history.append(result)
        return result
    
    def get_history(self) -> List[Dict]:
        return self.history


class PageTranslator:
    def __init__(self, translator: Translator):
        self.translator = translator
        self.auto_translate = False
        self.preferred_langs: List[str] = []
    
    def should_translate(self, url: str) -> bool:
        if not self.auto_translate:
            return False
        
        domain = url.split('/')[2] if '://' in url else url.split('/')[0]
        
        foreign_domains = ['.ru', '.ua', '.by', '.cn', '.jp', '.kr']
        
        for ext in foreign_domains:
            if domain.endswith(ext):
                return True
        
        return False
    
    def translate_element(self, element: str, target: str = None) -> str:
        result = self.translator.translate(element, target=target or self.translator.target_lang)
        if result:
            return result.translated
        return element
    
    def translate_page_text(self, text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        translated = []
        for sentence in sentences:
            result = self.translator.translate(sentence)
            if result:
                translated.append(result.translated)
            else:
                translated.append(sentence)
        
        return ' '.join(translated)
    
    def inject_translation_script(self, target_lang: str) -> str:
        script = f'''
        <script>
        function translatePage() {{
            // Translation placeholder
        }}
        </script>
        '''
        return script
