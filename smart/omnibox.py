import re
import json
import os
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser('~/.simple_browser')
OMNIBOX_FILE = os.path.join(DATA_DIR, 'omnibox.json')


class SearchEngine:
    def __init__(self, name: str, url: str, icon: str = ''):
        self.name = name
        self.url = url
        self.icon = icon
        self.shortcut = ''
    
    def format_url(self, query: str) -> str:
        return self.url.format(query=query.replace(' ', '+'))


class QuickCommand:
    def __init__(self, command: str, name: str, url: str = '', 
                 icon: str = '', action: str = 'search'):
        self.command = command
        self.name = name
        self.url = url
        self.icon = icon
        self.action = action
    
    def matches(self, query: str) -> bool:
        return query.startswith(self.command + ' ') or query == self.command


class OmniboxSuggestion:
    def __init__(self, text: str, url: str, source: str, 
                 icon: str = '', description: str = ''):
        self.text = text
        self.url = url
        self.source = source
        self.icon = icon
        self.description = description


class Omnibox:
    def __init__(self):
        self.suggestions: List[OmniboxSuggestion] = []
        self.search_engines: List[SearchEngine] = []
        self.quick_commands: List[QuickCommand] = []
        self.default_engine: Optional[SearchEngine] = None
        self.history_suggestions: List[Dict] = []
        self.bookmark_suggestions: List[Dict] = []
        
        self._load_default_engines()
        self._load_default_commands()
        self._load()
    
    def _load_default_engines(self):
        engines = [
            SearchEngine('Google', 'https://www.google.com/search?q={query}', '🔍'),
            SearchEngine('DuckDuckGo', 'https://duckduckgo.com/?q={query}', '🦆'),
            SearchEngine('Bing', 'https://www.bing.com/search?q={query}', '📊'),
            SearchEngine('Yandex', 'https://yandex.ru/search/?text={query}', '🔎'),
            SearchEngine('YouTube', 'https://www.youtube.com/results?search_query={query}', '▶️'),
            SearchEngine('Wikipedia', 'https://en.wikipedia.org/wiki/{query}', '📚'),
        ]
        
        for engine in engines:
            engine.shortcut = engine.name.lower()[:2] + ':'
        
        self.search_engines = engines
        self.default_engine = engines[0]
    
    def _load_default_commands(self):
        self.quick_commands = [
            QuickCommand('g:', 'Google Search', 'https://www.google.com/search?q={query}', '🔍', 'search'),
            QuickCommand('y:', 'YouTube', 'https://www.youtube.com/results?search_query={query}', '▶️', 'search'),
            QuickCommand('w:', 'Wikipedia', 'https://en.wikipedia.org/wiki/{query}', '📚', 'search'),
            QuickCommand('r:', 'Reddit', 'https://www.reddit.com/search/?q={query}', '🔴', 'search'),
            QuickCommand('gh:', 'GitHub', 'https://github.com/search?q={query}', '🐙', 'search'),
            QuickCommand('gm:', 'Gmail', 'https://mail.google.com/mail/u/0/#inbox?compose=new', '📧', 'url'),
            QuickCommand('ddg:', 'DuckDuckGo', 'https://duckduckgo.com/?q={query}', '🦆', 'search'),
            QuickCommand('imdb:', 'IMDb', 'https://www.imdb.com/find?q={query}', '🎬', 'search'),
            QuickCommand('amz:', 'Amazon', 'https://www.amazon.com/s?k={query}', '🛒', 'search'),
            QuickCommand('so:', 'Stack Overflow', 'https://stackoverflow.com/search?q={query}', '💼', 'search'),
            QuickCommand('tw:', 'Twitter', 'https://twitter.com/search?q={query}', '🐦', 'search'),
            QuickCommand('news:', 'News', 'https://news.google.com/search?q={query}', '📰', 'search'),
            QuickCommand('maps:', 'Maps', 'https://www.google.com/maps/search/{query}', '🗺️', 'search'),
            QuickCommand('tr:', 'Translate', 'https://translate.google.com/?sl=auto&tl=en&text={query}', '🌐', 'search'),
            QuickCommand('calc:', 'Calculator', '', '🧮', 'action'),
            QuickCommand('tab:', 'New Tab', '', '➕', 'action'),
            QuickCommand('bookmarks:', 'Bookmarks', '', '⭐', 'action'),
            QuickCommand('history:', 'History', '', '📜', 'action'),
            QuickCommand('downloads:', 'Downloads', '', '⬇️', 'action'),
            QuickCommand('settings:', 'Settings', '', '⚙️', 'action'),
        ]
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(OMNIBOX_FILE):
            try:
                with open(OMNIBOX_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history_suggestions = data.get('history', [])
            except:
                pass
    
    def _save(self):
        data = {
            'history': self.history_suggestions
        }
        with open(OMNIBOX_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def search(self, query: str, history: List[Dict] = None, 
               bookmarks: List[Dict] = None) -> List[OmniboxSuggestion]:
        self.suggestions = []
        
        if not query:
            return self.suggestions
        
        query = query.strip()
        
        self._check_quick_command(query)
        
        self._search_history(query, history)
        
        self._search_bookmarks(query, bookmarks)
        
        self._search_web(query)
        
        return self.suggestions[:10]
    
    def _check_quick_command(self, query: str):
        for cmd in self.quick_commands:
            if cmd.matches(query):
                if cmd.action == 'search':
                    search_query = query[len(cmd.command) + 1:] if ' ' in query else ''
                    url = cmd.url.format(query=search_query.replace(' ', '+'))
                    self.suggestions.append(OmniboxSuggestion(
                        f"{cmd.name}: {search_query}", url, 'command', cmd.icon
                    ))
                elif cmd.action == 'action':
                    self.suggestions.append(OmniboxSuggestion(
                        cmd.name, cmd.command, 'command', cmd.icon
                    ))
                break
    
    def _search_history(self, query: str, history: List[Dict] = None):
        if not history:
            return
        
        query_lower = query.lower()
        
        for item in history[:20]:
            url = item.get('url', '')
            title = item.get('title', url)
            
            if query_lower in url.lower() or query_lower in title.lower():
                self.suggestions.append(OmniboxSuggestion(
                    title[:50], url, 'history', '📜'
                ))
    
    def _search_bookmarks(self, query: str, bookmarks: List[Dict] = None):
        if not bookmarks:
            return
        
        query_lower = query.lower()
        
        for item in bookmarks[:10]:
            url = item.get('url', '')
            title = item.get('title', url)
            
            if query_lower in title.lower() or query_lower in url.lower():
                self.suggestions.append(OmniboxSuggestion(
                    title[:50], url, 'bookmark', '⭐'
                ))
    
    def _search_web(self, query: str):
        if self.default_engine:
            url = self.default_engine.format_url(query)
            self.suggestions.append(OmniboxSuggestion(
                f"Search: {query}", url, 'search', '🔍'
            ))
    
    def add_to_history(self, query: str, url: str):
        for item in self.history_suggestions:
            if item.get('url') == url:
                item['last_used'] = datetime.now().isoformat()
                item['use_count'] = item.get('use_count', 0) + 1
                self._save()
                return
        
        self.history_suggestions.insert(0, {
            'query': query,
            'url': url,
            'last_used': datetime.now().isoformat(),
            'use_count': 1
        })
        
        self.history_suggestions = self.history_suggestions[:100]
        self._save()
    
    def get_most_visited(self, limit: int = 10) -> List[OmniboxSuggestion]:
        sorted_history = sorted(
            self.history_suggestions,
            key=lambda x: x.get('use_count', 0),
            reverse=True
        )
        
        return [
            OmniboxSuggestion(item.get('title', item['url'])[:50], 
                            item['url'], 'history', '📜')
            for item in sorted_history[:limit]
            if 'url' in item
        ]
    
    def parse_input(self, user_input: str) -> Dict[str, any]:
        user_input = user_input.strip()
        
        if not user_input:
            return {'type': 'empty', 'url': ''}
        
        if user_input.startswith('http://') or user_input.startswith('https://'):
            return {'type': 'url', 'url': user_input}
        
        for cmd in self.quick_commands:
            if user_input.startswith(cmd.command + ' '):
                query = user_input[len(cmd.command) + 1:]
                return {
                    'type': 'command',
                    'command': cmd.command,
                    'query': query,
                    'url': cmd.url.format(query=query.replace(' ', '+')) if cmd.url else ''
                }
        
        if '.' in user_input and ' ' not in user_input and not user_input.startswith('.'):
            return {'type': 'url', 'url': 'https://' + user_input}
        
        return {'type': 'search', 'query': user_input}
    
    def set_default_engine(self, engine_name: str):
        for engine in self.search_engines:
            if engine.name.lower() == engine_name.lower():
                self.default_engine = engine
                break
    
    def add_search_engine(self, name: str, url: str, shortcut: str = ''):
        engine = SearchEngine(name, url)
        engine.shortcut = shortcut
        self.search_engines.append(engine)
    
    def get_search_engines(self) -> List[Dict]:
        return [{'name': e.name, 'url': e.url, 'shortcut': e.shortcut, 'icon': e.icon} 
                for e in self.search_engines]
    
    def add_quick_command(self, command: str, name: str, url: str = '', action: str = 'search'):
        cmd = QuickCommand(command, name, url, action=action)
        self.quick_commands.append(cmd)
    
    def get_autocomplete(self, partial: str) -> List[str]:
        results = []
        
        for cmd in self.quick_commands:
            if cmd.command.startswith(partial):
                results.append(cmd.command)
        
        for engine in self.search_engines:
            if engine.shortcut and engine.shortcut.startswith(partial):
                results.append(engine.shortcut)
        
        return results[:5]


class URLValidator:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def is_secure_url(url: str) -> bool:
        return url.startswith('https://')
    
    @staticmethod
    def extract_domain(url: str) -> str:
        if '://' in url:
            domain = url.split('/')[2]
        else:
            domain = url.split('/')[0]
        return domain.split(':')[0]
    
    @staticmethod
    def clean_url(url: str) -> str:
        url = url.strip()
        
        if not url.startswith('http://') and not url.startswith('https://'):
            if '.' in url and ' ' not in url:
                url = 'https://' + url
            else:
                return None
        
        return url


class URLShortener:
    def __init__(self):
        self.custom_shortcuts: Dict[str, str] = {}
    
    def shorten(self, url: str, service: str = 'tinyurl') -> str:
        try:
            if service == 'tinyurl':
                import requests
                response = requests.get(f'https://tinyurl.com/api-create.php?url={url}', timeout=5)
                if response.status_code == 200:
                    return response.text
        except:
            pass
        return url
    
    def expand(self, url: str) -> str:
        return url
    
    def add_shortcut(self, shortcut: str, url: str):
        self.custom_shortcuts[shortcut] = url
    
    def get_shortcut(self, shortcut: str) -> Optional[str]:
        return self.custom_shortcuts.get(shortcut)
