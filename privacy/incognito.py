import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DATA_DIR = os.path.expanduser('~/.simple_browser')


class IncognitoSession:
    def __init__(self):
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.start_time = datetime.now()
        self.history: List[Dict] = []
        self.cookies: Dict[str, Dict] = {}
        self.bookmarks: List[Dict] = []
        self.passwords: List[Dict] = []
        self.cache: Dict[str, any] = {}
    
    def add_to_history(self, url: str, title: str = ''):
        self.history.append({
            'url': url,
            'title': title,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_cookie(self, domain: str, name: str, value: str):
        if domain not in self.cookies:
            self.cookies[domain] = {}
        self.cookies[domain][name] = value
    
    def add_bookmark(self, url: str, title: str):
        self.bookmarks.append({
            'url': url,
            'title': title,
            'added_at': datetime.now().isoformat()
        })
    
    def add_password(self, url: str, username: str, password: str):
        self.passwords.append({
            'url': url,
            'username': username,
            'password': password,
            'timestamp': datetime.now().isoformat()
        })
    
    def clear_history(self):
        self.history = []
    
    def clear_cookies(self):
        self.cookies = {}
    
    def clear_all(self):
        self.clear_history()
        self.clear_cookies()
        self.bookmarks = []
        self.passwords = []
        self.cache = {}
    
    def get_duration(self) -> timedelta:
        return datetime.now() - self.start_time
    
    def get_stats(self) -> Dict:
        return {
            'session_id': self.session_id,
            'duration': str(self.get_duration()),
            'pages_visited': len(self.history),
            'cookies_count': sum(len(c) for c in self.cookies.values()),
            'bookmarks_added': len(self.bookmarks),
            'passwords_saved': len(self.passwords)
        }


class IncognitoManager:
    def __init__(self):
        self.active_session: Optional[IncognitoSession] = None
        self.session_history: List[Dict] = []
        self.auto_enable = False
        self.show_notifications = True
    
    def start_session(self) -> IncognitoSession:
        if self.active_session:
            self.end_session()
        
        self.active_session = IncognitoSession()
        return self.active_session
    
    def end_session(self, save_history: bool = False):
        if not self.active_session:
            return
        
        if not save_history:
            self.active_session.clear_all()
        
        stats = self.active_session.get_stats()
        self.session_history.append({
            'session_id': self.active_session.session_id,
            'stats': stats,
            'ended_at': datetime.now().isoformat()
        })
        
        self.active_session = None
    
    def is_active(self) -> bool:
        return self.active_session is not None
    
    def get_current_session(self) -> Optional[IncognitoSession]:
        return self.active_session
    
    def add_to_history(self, url: str, title: str = ''):
        if self.active_session:
            self.active_session.add_to_history(url, title)
    
    def add_cookie(self, domain: str, name: str, value: str):
        if self.active_session:
            self.active_session.add_cookie(domain, name, value)
    
    def get_cookies(self, domain: str = None) -> Dict:
        if not self.active_session:
            return {}
        
        if domain:
            return self.active_session.cookies.get(domain, {})
        return self.active_session.cookies
    
    def get_session_stats(self) -> Optional[Dict]:
        if self.active_session:
            return self.active_session.get_stats()
        return None
    
    def get_session_history(self) -> List[Dict]:
        return self.session_history
    
    def set_auto_enable(self, enabled: bool):
        self.auto_enable = enabled
    
    def set_notifications(self, enabled: bool):
        self.show_notifications = enabled
    
    def clear_all_sessions(self):
        self.session_history = []


class IncognitoIndicator:
    @staticmethod
    def get_icon(is_active: bool) -> str:
        return '👁️' if is_active else '🌐'
    
    @staticmethod
    def get_color(is_active: bool) -> str:
        return '#FF5722' if is_active else '#2196F3'
    
    @staticmethod
    def get_warning_message() -> str:
        return (
            "Вы в режиме инкогнито.\n\n"
            "Ваша история посещений, cookies и данные сайтов не будут сохранены "
            "после закрытия всех вкладок инкогнито.\n\n"
            "Это не влияет на:\n"
            "- Загрузки\n"
            "- Закладки\n"
            "- Пароли сохраненные в менеджере паролей"
        )
