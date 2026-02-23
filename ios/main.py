import os
import json
import re
import base64
import hashlib
import random
import string
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.recycleview import RecycleView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.videoplayer import VideoPlayer
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.utils import get_color_from_hex

try:
    from pyobjus import autoclass, objc_str, NSObject
    import UIKit
    IOS = True
except:
    IOS = False


# ==================== КОНФИГУРАЦИЯ ====================
class Config:
    def __init__(self):
        self.store = JsonStore('browser_config.json')
        
    def get(self, key, default=None):
        try:
            return self.store.get(key)
        except:
            return default
            
    def set(self, key, value):
        self.store.put(key, value)
        
    def get_bool(self, key, default=False):
        val = self.get(key, default)
        return bool(val)
        
    def get_int(self, key, default=0):
        val = self.get(key, default)
        return int(val)


# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self, name='browser.db'):
        self.conn = sqlite3.connect(name, check_same_thread=False)
        self.create_tables()
        
    def create_tables(self):
        c = self.conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS history
                     (id INTEGER PRIMARY KEY, url TEXT, title TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                     (id INTEGER PRIMARY KEY, url TEXT, title TEXT,
                      folder TEXT DEFAULT '', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS passwords
                     (id INTEGER PRIMARY KEY, url TEXT, username TEXT,
                      password TEXT, notes TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS tabs
                     (id INTEGER PRIMARY KEY, url TEXT, title TEXT,
                      favicon TEXT, position INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS cookies
                     (id INTEGER PRIMARY KEY, domain TEXT, name TEXT,
                      value TEXT, expiry DATETIME)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS achievements
                     (id INTEGER PRIMARY KEY, name TEXT, description TEXT,
                      unlocked INTEGER DEFAULT 0, timestamp DATETIME)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS todos
                     (id INTEGER PRIMARY KEY, text TEXT, done INTEGER DEFAULT 0,
                      priority TEXT DEFAULT 'medium', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')
                       
        c.execute('''CREATE TABLE IF NOT EXISTS cloud_bookmarks
                     (id INTEGER PRIMARY KEY, url TEXT, title TEXT,
                      folder TEXT DEFAULT '', sync_id TEXT UNIQUE,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                       
        self.conn.commit()
        
    def execute(self, query, params=()):
        c = self.conn.cursor()
        c.execute(query, params)
        self.conn.commit()
        return c
        
    def fetchall(self, query, params=()):
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchall()
        
    def fetchone(self, query, params=()):
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchone()


# ==================== МЕНЕДЖЕР ПАРОЛЕЙ ====================
class PasswordManager:
    def __init__(self, db):
        self.db = db
        self.master_password = None
        self.key = None
        
    def set_master_password(self, password):
        self.master_password = password
        self.key = hashlib.sha256(password.encode()).digest()[:16]
        
    def verify_master_password(self, password):
        return self.master_password == password
        
    def encrypt(self, text):
        if not self.key:
            return text
        encrypted = []
        for i, c in enumerate(text):
            encrypted.append(chr(ord(c) ^ ord(self.key[i % len(self.key)])))
        return base64.b64encode(''.join(encrypted).encode()).decode()
        
    def decrypt(self, text):
        if not self.key:
            return text
        try:
            decoded = base64.b64decode(text.encode()).decode()
            decrypted = []
            for i, c in enumerate(decoded):
                decrypted.append(chr(ord(c) ^ ord(self.key[i % len(self.key)])))
            return ''.join(decrypted)
        except:
            return text
            
    def generate_password(self, length=16, use_special=True):
        chars = string.ascii_letters + string.digits
        if use_special:
            chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        return ''.join(random.choice(chars) for _ in range(length))
        
    def save_password(self, url, username, password, notes=''):
        encrypted_pass = self.encrypt(password)
        self.db.execute(
            'INSERT INTO passwords (url, username, password, notes) VALUES (?, ?, ?, ?)',
            (url, username, encrypted_pass, notes)
        )
        
    def get_passwords(self):
        rows = self.db.fetchall('SELECT url, username, password, notes FROM passwords')
        return [(r[0], r[1], self.decrypt(r[2]), r[3]) for r in rows]
        
    def find_password(self, url):
        row = self.db.fetchone(
            'SELECT username, password FROM passwords WHERE url LIKE ?',
            (f'%{url}%',)
        )
        if row:
            return row[0], self.decrypt(row[1])
        return None, None
        
    def delete_password(self, url):
        self.db.execute('DELETE FROM passwords WHERE url = ?', (url,))


# ==================== БЛОКИРОВЩИК РЕКЛАМЫ ====================
class AdBlocker:
    def __init__(self):
        self.enabled = True
        self.filters = [
            r'.*\.doubleclick\.net',
            r'.*\.googlesyndication\.com',
            r'.*\.googleadservices\.com',
            r'.*\.adnxs\.com',
            r'.*\.adsrvr\.org',
            r'.*\.advertising\.com',
            r'.*\.amazon-adsystem\.com',
            r'.*\.facebook\.com/tr',
            r'.*\.bing\.com/bat',
            r'.*\.taboola\.com',
            r'.*\.outbrain\.com',
            r'.*\.criteo\.com',
            r'.*\.popads\.net',
            r'.*\.popcash\.net',
        ]
        self.compiled = [re.compile(f) for f in self.filters]
        
    def should_block(self, url):
        if not self.enabled:
            return False
        for pattern in self.compiled:
            if pattern.match(url):
                return True
        return False
        
    def add_filter(self, pattern):
        try:
            self.filters.append(pattern)
            self.compiled.append(re.compile(pattern))
        except:
            pass
            
    def toggle(self):
        self.enabled = not self.enabled


# ==================== РЕЖИМ КОНФИДЕНЦИАЛЬНОСТИ ====================
class PrivacyMode:
    def __init__(self, db):
        self.db = db
        self.incognito = False
        self.dnt = True
        self.block_trackers = True
        self.auto_delete_cookies = False
        self.block_cryptominers = True
        self.fingerprint_protection = False
        
    def clear_history(self):
        self.db.execute('DELETE FROM history')
        
    def clear_cookies(self):
        self.db.execute('DELETE FROM cookies')
        
    def clear_all(self):
        self.clear_history()
        self.clear_cookies()
        
    def set_incognito(self, enabled):
        self.incognito = enabled


# ==================== VPN/ПРОКСИ ====================
class VPNManager:
    def __init__(self):
        self.connected = False
        self.server = None
        self.proxies = [
            {'host': 'proxy1.example.com', 'port': 8080, 'country': 'US'},
            {'host': 'proxy2.example.com', 'port': 8080, 'country': 'DE'},
            {'host': 'proxy3.example.com', 'port': 8080, 'country': 'JP'},
        ]
        
    def connect(self, server=None):
        if server:
            self.server = server
        else:
            self.server = random.choice(self.proxies)
        self.connected = True
        
    def disconnect(self):
        self.connected = False
        self.server = None


# ==================== ОМНИБОКС ====================
class Omnibox:
    def __init__(self, db):
        self.db = db
        self.suggestions = []
        
    def search(self, query):
        results = []
        
        history = self.db.fetchall(
            'SELECT url, title FROM history WHERE url LIKE ? OR title LIKE ? LIMIT 5',
            (f'%{query}%', f'%{query}%')
        )
        results.extend([('history', r[0], r[1]) for r in history])
        
        bookmarks = self.db.fetchall(
            'SELECT url, title FROM bookmarks WHERE url LIKE ? OR title LIKE ? LIMIT 5',
            (f'%{query}%', f'%{query}%')
        )
        results.extend([('bookmark', r[0], r[1]) for r in bookmarks])
        
        quick_commands = {
            'g:': 'Google Search',
            'y:': 'YouTube',
            'w:': 'Wikipedia',
            'r:': 'Reddit',
            'gh:': 'GitHub',
            'gm:': 'Gmail',
        }
        for cmd, name in quick_commands.items():
            if query.startswith(cmd) or query.startswith(name.lower()):
                results.append(('command', cmd, name))
                
        return results[:10]
        
    def add_to_history(self, url, title):
        self.db.execute(
            'INSERT INTO history (url, title) VALUES (?, ?)',
            (url, title)
        )
        
    def add_bookmark(self, url, title, folder=''):
        self.db.execute(
            'INSERT INTO bookmarks (url, title, folder) VALUES (?, ?, ?)',
            (url, title, folder)
        )


# ==================== TTS (TEXT TO SPEECH) ====================
class TTSManager:
    def __init__(self):
        self.speaking = False
        self.rate = 1.0
        self.pitch = 1.0
        
    def speak(self, text):
        if IOS:
            try:
                AVSpeechSynthesizer = autoclass('AVSpeechSynthesizer')
                AVSpeechUtterance = autoclass('AVSpeechUtterance')
                synthesizer = AVSpeechSynthesizer.alloc().init()
                utterance = AVSpeechUtterance.speechUtteranceWithString_(text)
                utterance.setRate_(0.5)
                synthesizer.speakUtterance_(utterance)
                self.speaking = True
            except:
                pass
                
    def stop(self):
        self.speaking = False


# ==================== ПЕРЕВОДЧИК ====================
class Translator:
    def __init__(self):
        self.languages = {
            'en': 'English',
            'ru': 'Русский',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
            'zh': '中文',
            'ja': '日本語',
            'ko': '한국어',
        }
        
    def detect_language(self, text):
        return 'en'
        
    def translate(self, text, from_lang='auto', to_lang='en'):
        return f'[{to_lang}] {text}'


# ==================== RSS РИДЕР ====================
class RSSReader:
    def __init__(self):
        self.feeds = []
        
    def add_feed(self, url, name=''):
        self.feeds.append({'url': url, 'name': name or url})
        
    def parse_feed(self, url):
        return [
            {'title': 'Sample Article 1', 'link': url, 'description': 'Sample description'},
            {'title': 'Sample Article 2', 'link': url, 'description': 'Sample description'},
        ]


# ==================== РЕЖИМ ЧТЕНИЯ ====================
class ReaderMode:
    def __init__(self):
        self.enabled = False
        
    def extract_text(self, html):
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# ==================== СИНХРОНИЗАЦИЯ ====================
class SyncManager:
    def __init__(self, db):
        self.db = db
        self.connected = False
        self.last_sync = None
        self.cloud_url = "https://simplebrowser-sync.example.com"
        self.device_id = hashlib.md5(str(time.time()).encode()).hexdigest()
        
    def generate_qr_code(self):
        import qrcode
        data = json.dumps({
            'device_id': self.device_id,
            'sync_url': self.cloud_url,
        })
        img = qrcode.make(data)
        img.save('sync_qr.png')
        return 'sync_qr.png'
        
    def export_profile(self, filename):
        data = {
            'history': self.db.fetchall('SELECT * FROM history'),
            'bookmarks': self.db.fetchall('SELECT * FROM bookmarks'),
            'passwords': self.db.fetchall('SELECT url, username FROM passwords'),
            'settings': self.db.fetchall('SELECT * FROM settings'),
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
            
    def import_profile(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        for item in data.get('history', []):
            self.db.execute('INSERT INTO history (url, title) VALUES (?, ?)', (item[1], item[2]))
        for item in data.get('bookmarks', []):
            self.db.execute('INSERT INTO bookmarks (url, title, folder) VALUES (?, ?, ?)', 
                          (item[1], item[2], item[3]))
            
    def sync_with_pc(self, pc_ip=None):
        if pc_ip:
            self.cloud_url = f"http://{pc_ip}:8765"
        self.connected = True
        self.last_sync = datetime.now()
        return True
        
    def get_sync_status(self):
        return {
            'connected': self.connected,
            'last_sync': self.last_sync,
            'device_id': self.device_id,
        }


# ==================== ОБЛАЧНЫЕ ЗАКЛАДКИ ====================
class CloudBookmarks:
    def __init__(self, db):
        self.db = db
        self.sync_enabled = False
        self.cloud_url = "https://simplebrowser-sync.example.com/api/bookmarks"
        
    def add_cloud_bookmark(self, url, title, folder=''):
        sync_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()
        self.db.execute(
            'INSERT INTO cloud_bookmarks (url, title, folder, sync_id) VALUES (?, ?, ?, ?)',
            (url, title, folder, sync_id)
        )
        return sync_id
        
    def get_cloud_bookmarks(self):
        return self.db.fetchall('SELECT url, title, folder, sync_id FROM cloud_bookmarks')
        
    def sync_bookmarks(self):
        if not self.sync_enabled:
            return []
        bookmarks = self.get_cloud_bookmarks()
        return [{'url': b[0], 'title': b[1], 'folder': b[2], 'sync_id': b[3]} for b in bookmarks]
        
    def import_from_cloud(self, cloud_data):
        for item in cloud_data:
            self.db.execute(
                '''INSERT OR REPLACE INTO cloud_bookmarks (url, title, folder, sync_id) 
                   VALUES (?, ?, ?, ?)''',
                (item.get('url'), item.get('title'), item.get('folder', ''), item.get('sync_id'))
            )
            
    def toggle_sync(self):
        self.sync_enabled = not self.sync_enabled
        return self.sync_enabled


# ==================== МЕДИА ФУНКЦИИ ====================
class MediaManager:
    def __init__(self):
        self.screenshots = []
        self.downloads = []
        
    def take_screenshot(self, widget):
        try:
            Window.screenshot(name='screenshot.png')
            return True
        except:
            return False
            
    def download_video(self, url, filename):
        self.downloads.append({'url': url, 'filename': filename, 'status': 'downloading'})
        threading.Thread(target=self._download_file, args=(url, filename)).start()
        
    def _download_file(self, url, filename):
        try:
            import requests
            r = requests.get(url, stream=True)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            for d in self.downloads:
                if d['filename'] == filename:
                    d['status'] = 'completed'
        except:
            for d in self.downloads:
                if d['filename'] == filename:
                    d['status'] = 'failed'


# ==================== ПРОДУКТИВНОСТЬ ====================
class PomodoroTimer:
    def __init__(self):
        self.work_duration = 25 * 60
        self.break_duration = 5 * 60
        self.running = False
        self.time_left = self.work_duration
        self.sessions = 0
        
    def start(self):
        self.running = True
        self.time_left = self.work_duration
        
    def pause(self):
        self.running = False
        
    def reset(self):
        self.running = False
        self.time_left = self.work_duration
        
    def tick(self):
        if self.running and self.time_left > 0:
            self.time_left -= 1
            return True
        elif self.time_left == 0:
            self.sessions += 1
            self.time_left = self.break_duration if self.sessions % 4 == 0 else self.work_duration
            return True
        return False
        
    def get_formatted_time(self):
        mins = self.time_left // 60
        secs = self.time_left % 60
        return f"{mins:02d}:{secs:02d}"


class SiteBlocker:
    def __init__(self, db):
        self.db = db
        self.blocked_sites = []
        self.enabled = False
        
    def add_site(self, site):
        if site not in self.blocked_sites:
            self.blocked_sites.append(site)
            
    def remove_site(self, site):
        if site in self.blocked_sites:
            self.blocked_sites.remove(site)
            
    def should_block(self, url):
        if not self.enabled:
            return False
        for site in self.blocked_sites:
            if site in url:
                return True
        return False


class TodoManager:
    def __init__(self, db):
        self.db = db
        
    def add_todo(self, text, priority='medium'):
        self.db.execute(
            'INSERT INTO todos (text, priority) VALUES (?, ?)',
            (text, priority)
        )
        
    def get_todos(self):
        return self.db.fetchall('SELECT id, text, done, priority FROM todos ORDER BY done, priority')
        
    def toggle_todo(self, id):
        self.db.execute('UPDATE todos SET done = NOT done WHERE id = ?', (id,))
        
    def delete_todo(self, id):
        self.db.execute('DELETE FROM todos WHERE id = ?', (id,))


class TimeTracker:
    def __init__(self, db):
        self.db = db
        self.sites = {}
        
    def track_visit(self, url, duration):
        domain = url.split('/')[2] if len(url.split('/')) > 2 else url
        if domain not in self.sites:
            self.sites[domain] = 0
        self.sites[domain] += duration
        
    def get_stats(self):
        return sorted(self.sites.items(), key=lambda x: x[1], reverse=True)[:10]


# ==================== AI ФУНКЦИИ ====================
class AIManager:
    def __init__(self):
        self.api_key = None
        
    def set_api_key(self, key):
        self.api_key = key
        
    def summarize_page(self, text):
        if self.api_key:
            return f"[AI Summary] {text[:200]}..."
        return "Настройте API ключ для AI функций"
        
    def answer_question(self, question, context):
        if self.api_key:
            return f"[AI Answer] This is a simulated answer to: {question}"
        return "Настройте API ключ для AI функций"
        
    def categorize_bookmark(self, url, title):
        categories = ['news', 'social', 'shopping', 'work', 'entertainment', 'education']
        return random.choice(categories)


# ==================== ГЕЙМИФИКАЦИЯ ====================
class AchievementManager:
    def __init__(self, db):
        self.db = db
        self.points = 0
        self.achievements = [
            {'id': 1, 'name': 'Первая вкладка', 'desc': 'Откройте первую вкладку', 'points': 10},
            {'id': 2, 'name': 'Закладодная', 'desc': 'Добавьте первую закладку', 'points': 20},
            {'id': 3, 'name': 'Серфинг', 'desc': 'Посетите 10 сайтов', 'points': 50},
            {'id': 4, 'name': 'Безопасник', 'desc': 'Включите блокировку рекламы', 'points': 30},
            {'id': 5, 'name': 'Помодоро', 'desc': 'Завершите 4 Pomodoro сессии', 'points': 100},
            {'id': 6, 'name': 'Чтец', 'desc': 'Используйте режим чтения', 'points': 25},
            {'id': 7, 'name': 'Приватность', 'desc': 'Используйте инкогнито режим', 'points': 40},
            {'id': 8, 'name': 'Эксперт', 'desc': 'Посетите 100 сайтов', 'points': 200},
            {'id': 9, 'name': 'Облако', 'desc': 'Синхронизируйте закладки', 'points': 50},
        ]
        
    def unlock(self, achievement_id):
        for ach in self.achievements:
            if ach['id'] == achievement_id:
                self.db.execute(
                    'INSERT OR IGNORE INTO achievements (name, description, unlocked, timestamp) VALUES (?, ?, 1, datetime("now"))',
                    (ach['name'], ach['desc'])
                )
                self.points += ach['points']
                return ach['name']
        return None
        
    def get_unlocked(self):
        return self.db.fetchall('SELECT name, description FROM achievements WHERE unlocked = 1')


class MiniGames:
    def __init__(self):
        self.games = ['snake', 'pong', 'tetris']
        
    def get_random_game(self):
        return random.choice(self.games)


# ==================== БЕЗОПАСНОСТЬ ====================
class SecurityManager:
    def __init__(self):
        self.virustotal_api_key = None
        
    def check_phishing(self, url):
        suspicious = ['login', 'signin', 'account', 'verify', 'secure', 'bank']
        for word in suspicious:
            if word in url.lower():
                return True, 'Подозрительный URL'
        return False, 'Безопасный'
        
    def check_ssl(self, url):
        return url.startswith('https://')


# ==================== УВЕДОМЛЕНИЯ ====================
class NotificationManager:
    def __init__(self):
        self.dnd = False
        self.enabled = True
        
    def show(self, title, message):
        if not self.enabled or self.dnd:
            return
        if IOS:
            try:
                UNUserNotificationCenter = autoclass('UNUserNotificationCenter')
                center = UNUserNotificationCenter.currentNotificationCenter()
                content = NSNotificationAction.alloc()
            except:
                pass


# ==================== ОСНОВНОЕ ПРИЛОЖЕНИЕ ====================
class BrowserApp(App):
    current_url = StringProperty('https://www.google.com')
    title = StringProperty('Simple Browser')
    loading = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.config = Config()
        
        self.password_manager = PasswordManager(self.db)
        self.ad_blocker = AdBlocker()
        self.privacy = PrivacyMode(self.db)
        self.vpn = VPNManager()
        self.omnibox = Omnibox(self.db)
        self.tts = TTSManager()
        self.translator = Translator()
        self.rss = RSSReader()
        self.reader = ReaderMode()
        self.sync = SyncManager(self.db)
        self.cloud_bookmarks = CloudBookmarks(self.db)
        self.media = MediaManager()
        self.pomodoro = PomodoroTimer()
        self.site_blocker = SiteBlocker(self.db)
        self.todos = TodoManager(self.db)
        self.time_tracker = TimeTracker(self.db)
        self.ai = AIManager()
        self.achievements = AchievementManager(self.db)
        self.games = MiniGames()
        self.security = SecurityManager()
        self.notifications = NotificationManager()
        
        self.web_view = None
        self.tabs = []
        self.current_tab = 0
        
    def build(self):
        root = BoxLayout(orientation='vertical')
        
        self.toolbar = self.create_toolbar()
        root.add_widget(self.toolbar)
        
        self.url_bar = self.create_url_bar()
        root.add_widget(self.url_bar)
        
        self.content_area = BoxLayout()
        root.add_widget(self.content_area)
        
        self.bottom_bar = self.create_bottom_bar()
        root.add_widget(self.bottom_bar)
        
        return root
        
    def create_toolbar(self):
        toolbar = BoxLayout(size_hint_y=None, height=50)
        toolbar.orientation = 'horizontal'
        
        self.back_btn = Button(text='<', size_hint_x=None, width=40)
        self.back_btn.bind(on_press=self.go_back)
        toolbar.add_widget(self.back_btn)
        
        self.forward_btn = Button(text='>', size_hint_x=None, width=40)
        self.forward_btn.bind(on_press=self.go_forward)
        toolbar.add_widget(self.forward_btn)
        
        self.reload_btn = Button(text='↻', size_hint_x=None, width=40)
        self.reload_btn.bind(on_press=self.reload)
        toolbar.add_widget(self.reload_btn)
        
        self.home_btn = Button(text='⌂', size_hint_x=None, width=40)
        self.home_btn.bind(on_press=self.go_home)
        toolbar.add_widget(self.home_btn)
        
        self.menu_btn = Button(text='☰', size_hint_x=None, width=40)
        self.menu_btn.bind(on_press=self.show_menu)
        toolbar.add_widget(self.menu_btn)
        
        return toolbar
        
    def create_url_bar(self):
        url_bar = BoxLayout(size_hint_y=None, height=50, padding=5)
        
        self.url_input = TextInput(
            hint_text='Введите URL или поисковый запрос...',
            multiline=False,
            size_hint_x=0.85
        )
        self.url_input.bind(on_text_validate=self.load_url)
        url_bar.add_widget(self.url_input)
        
        self.go_btn = Button(text='→', size_hint_x=0.15)
        self.go_btn.bind(on_press=self.load_url)
        url_bar.add_widget(self.go_btn)
        
        return url_bar
        
    def create_bottom_bar(self):
        bottom = BoxLayout(size_hint_y=None, height=50)
        bottom.orientation = 'horizontal'
        
        buttons = [
            ('📑', self.show_tabs),
            ('⭐', self.show_bookmarks),
            ('🔒', self.show_passwords),
            ('⚙️', self.show_settings),
        ]
        
        for icon, callback in buttons:
            btn = Button(text=icon, size_hint_x=0.25)
            btn.bind(on_press=callback)
            bottom.add_widget(btn)
            
        return bottom

    def load_url(self, instance=None):
        url = self.url_input.text.strip()
        if not url:
            return
            
        if self.site_blocker.should_block(url):
            self.show_message('Сайт заблокирован')
            return
            
        if not url.startswith('http'):
            if ' ' in url:
                url = f'https://www.google.com/search?q={url}'
            else:
                url = 'https://' + url
                
        self.url_input.text = url
        self.omnibox.add_to_history(url, url)
        self.achievements.unlock(1)
        
    def go_back(self, instance):
        pass
        
    def go_forward(self, instance):
        pass
        
    def reload(self, instance):
        pass
        
    def go_home(self, instance):
        self.url_input.text = 'https://www.google.com'
        self.load_url(None)
        
    def show_menu(self, instance):
        menu = Popup(title='Меню', size_hint=(0.9, 0.8))
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        items = [
            ('🔍', 'Поиск', self.show_search),
            ('📚', 'Закладки', self.show_bookmarks),
            ('☁️', 'Облачные закладки', self.show_cloud_bookmarks),
            ('📜', 'История', self.show_history),
            ('🔑', 'Пароли', self.show_passwords),
            ('📱', 'Вкладки', self.show_tabs),
            ('🎯', 'AdBlock', self.show_adblock),
            ('🛡️', 'Приватность', self.show_privacy),
            ('📺', 'Режим чтения', self.toggle_reader),
            ('🔊', 'TTS', self.show_tts),
            ('🌐', 'Переводчик', self.show_translator),
            ('📰', 'RSS', self.show_rss),
            ('⏱️', 'Pomodoro', self.show_pomodoro),
            ('✅', 'Задачи', self.show_todos),
            ('🏆', 'Достижения', self.show_achievements),
            ('🎮', 'Игры', self.show_games),
            ('🔄', 'Синхронизация с ПК', self.show_sync),
            ('📷', 'Скриншот', self.take_screenshot),
            ('⚙️', 'Настройки', self.show_settings),
        ]
        
        for icon, label, callback in items:
            btn = Button(text=f'{icon} {label}', size_hint_y=None, height=50)
            btn.bind(on_press=lambda x, c=callback: (c(), menu.dismiss()))
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        menu.content = scroll
        menu.open()
        
    def show_message(self, msg):
        popup = Popup(title='Сообщение', size_hint=(0.8, 0.3))
        popup.content = Label(text=msg)
        popup.open()
        
    def show_search(self):
        self.show_menu(None)
        
    def show_bookmarks(self):
        popup = Popup(title='Закладки', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical')
        
        add_bookmark_btn = Button(text='+ Добавить закладку', size_hint_y=None, height=50)
        add_bookmark_btn.bind(on_press=lambda x: self.add_current_as_bookmark())
        content.add_widget(add_bookmark_btn)
        
        bookmarks = self.db.fetchall('SELECT url, title FROM bookmarks')
        for url, title in bookmarks:
            btn = Button(text=f'{title}\n{url}', size_hint_y=None, height=60)
            btn.bind(on_press=lambda x, u=url: (self.url_input.__setattr__('text', u), self.load_url(None), popup.dismiss()))
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def add_current_as_bookmark(self):
        url = self.url_input.text
        title = url
        self.omnibox.add_bookmark(url, title)
        self.show_message('Закладка добавлена!')
        self.achievements.unlock(2)
        
    def show_cloud_bookmarks(self):
        popup = Popup(title='Облачные закладки', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        sync_status = BoxLayout(size_hint_y=None, height=40)
        sync_status.add_widget(Label(text='Синхронизация:', size_hint_x=0.7))
        sync_switch = Switch(active=self.cloud_bookmarks.sync_enabled)
        sync_switch.bind(active=lambda x, v: self.cloud_bookmarks.toggle_sync())
        sync_status.add_widget(sync_switch)
        content.add_widget(sync_status)
        
        add_cloud_btn = Button(text='+ Добавить текущую в облако', size_hint_y=None, height=50)
        add_cloud_btn.bind(on_press=lambda x: self.add_to_cloud())
        content.add_widget(add_cloud_btn)
        
        sync_btn = Button(text='🔄 Синхронизировать', size_hint_y=None, height=50)
        sync_btn.bind(on_press=lambda x: self.achievements.unlock(9))
        content.add_widget(sync_btn)
        
        for url, title, folder, sync_id in self.cloud_bookmarks.get_cloud_bookmarks():
            btn = Button(text=f'{title}\n{url}', size_hint_y=None, height=60)
            btn.bind(on_press=lambda x, u=url: (self.url_input.__setattr__('text', u), self.load_url(None), popup.dismiss()))
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def add_to_cloud(self):
        url = self.url_input.text
        title = url
        self.cloud_bookmarks.add_cloud_bookmark(url, title)
        self.show_message('Добавлено в облако!')
        
    def show_history(self):
        popup = Popup(title='История', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical')
        
        history = self.db.fetchall('SELECT url, title, timestamp FROM history ORDER BY timestamp DESC LIMIT 50')
        for url, title, ts in history:
            btn = Button(text=f'{title}\n{ts}', size_hint_y=None, height=60)
            btn.bind(on_press=lambda x, u=url: (self.url_input.__setattr__('text', u), self.load_url(None), popup.dismiss()))
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def show_passwords(self):
        popup = Popup(title='Менеджер паролей', size_hint=(0.9, 0.8))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        master_section = BoxLayout(size_hint_y=None, height=50)
        master_section.add_widget(Label(text='Мастер-пароль:'))
        master_pass = TextInput(password=True, multiline=False, size_hint_x=0.6)
        master_section.add_widget(master_pass)
        unlock_btn = Button(text='Разблокировать', size_hint_x=0.4)
        unlock_btn.bind(on_press=lambda x: self.password_manager.set_master_password(master_pass.text))
        master_section.add_widget(unlock_btn)
        content.add_widget(master_section)
        
        add_section = BoxLayout(size_hint_y=None, height=50)
        add_section.add_widget(Label(text='URL:', size_hint_x=0.2))
        url_input = TextInput(size_hint_x=0.3)
        add_section.add_widget(url_input)
        add_section.add_widget(Label(text='Логин:', size_hint_x=0.2))
        user_input = TextInput(size_hint_x=0.3)
        add_section.add_widget(user_input)
        content.add_widget(add_section)
        
        gen_pass_btn = Button(text='Сгенерировать пароль', size_hint_y=None, height=40)
        gen_pass_btn.bind(on_press=lambda x: self.show_message(self.password_manager.generate_password()))
        content.add_widget(gen_pass_btn)
        
        passwords = self.password_manager.get_passwords()
        for url, username, password, notes in passwords[:10]:
            btn = Button(text=f'{url}\n{username}', size_hint_y=None, height=50)
            btn.bind(on_press=lambda x, p=password: self.show_message(f'Пароль: {p}'))
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def show_tabs(self):
        popup = Popup(title='Вкладки', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical')
        
        new_tab_btn = Button(text='+ Новая вкладка', size_hint_y=None, height=50)
        new_tab_btn.bind(on_press=lambda x: self.achievements.unlock(1))
        content.add_widget(new_tab_btn)
        
        for i, tab in enumerate(self.tabs):
            btn = Button(text=f'Вкладка {i+1}: {tab.get("title", "Новая")}', size_hint_y=None, height=50)
            content.add_widget(btn)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def show_adblock(self):
        popup = Popup(title='AdBlock', size_hint=(0.8, 0.5))
        content = BoxLayout(orientation='vertical', padding=10)
        
        status = BoxLayout(size_hint_y=None, height=50)
        status.add_widget(Label(text='Включен:'))
        switch = Switch(active=self.ad_blocker.enabled)
        switch.bind(active=lambda x, v: setattr(self.ad_blocker, 'enabled', v))
        status.add_widget(switch)
        content.add_widget(status)
        
        stats = Label(text=f'Фильтров: {len(self.ad_blocker.filters)}')
        content.add_widget(stats)
        
        if self.ad_blocker.enabled:
            content.add_widget(Button(text='Разблокировать (Achievement)', on_press=lambda x: self.achievements.unlock(4)))
            
        popup.content = content
        popup.open()
        
    def show_privacy(self):
        popup = Popup(title='Приватность', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        items = [
            ('Инкогнито', self.privacy.set_incognito),
            ('DNT', lambda x: setattr(self.privacy, 'dnt', True)),
            ('Блокировщик трекеров', lambda x: setattr(self.privacy, 'block_trackers', True)),
        ]
        
        for label, callback in items:
            row = BoxLayout(size_hint_y=None, height=40)
            row.add_widget(Label(text=label, size_hint_x=0.7))
            sw = Switch()
            sw.bind(active=lambda x, v, c=callback: c(v))
            row.add_widget(sw)
            content.add_widget(row)
            
        clear_btn = Button(text='Очистить историю и куки', size_hint_y=None, height=50)
        clear_btn.bind(on_press=lambda x: self.privacy.clear_all())
        content.add_widget(clear_btn)
        
        popup.content = content
        popup.open()
        
    def toggle_reader(self):
        self.reader.enabled = not self.reader.enabled
        self.show_message(f'Режим чтения: {"ВКЛ" if self.reader.enabled else "ВЫКЛ"}')
        if self.reader.enabled:
            self.achievements.unlock(6)
            
    def show_tts(self):
        popup = Popup(title='TTS (Чтение вслух)', size_hint=(0.8, 0.4))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        btn = Button(text='🔊 Читать страницу вслух')
        btn.bind(on_press=lambda x: self.tts.speak(self.url_input.text))
        content.add_widget(btn)
        
        btn_stop = Button(text='⏹ Остановить')
        btn_stop.bind(on_press=lambda x: self.tts.stop())
        content.add_widget(btn_stop)
        
        popup.content = content
        popup.open()
        
    def show_translator(self):
        popup = Popup(title='Переводчик', size_hint=(0.9, 0.6))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        content.add_widget(Label(text='Введите текст для перевода:'))
        text_input = TextInput(size_hint_y=0.3, multiline=True)
        content.add_widget(text_input)
        
        lang_spinner = Spinner(
            text='English',
            values=list(self.translator.languages.values()),
            size_hint_y=None,
            height=40
        )
        content.add_widget(lang_spinner)
        
        translate_btn = Button(text='Перевести')
        translate_btn.bind(on_press=lambda x: self.show_message(self.translator.translate(text_input.text)))
        content.add_widget(translate_btn)
        
        popup.content = content
        popup.open()
        
    def show_rss(self):
        popup = Popup(title='RSS Ридер', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        add_feed = BoxLayout(size_hint_y=None, height=40)
        add_feed.add_widget(TextInput(hint_text='URL ленты', size_hint_x=0.7))
        add_feed.add_widget(Button(text='+', size_hint_x=0.3))
        content.add_widget(add_feed)
        
        for feed in self.rss.feeds:
            btn = Button(text=feed['name'], size_hint_y=None, height=40)
            content.add_widget(btn)
            
        popup.content = content
        popup.open()
        
    def show_pomodoro(self):
        popup = Popup(title='Pomodoro Таймер', size_hint=(0.8, 0.5))
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.pomodoro_label = Label(text=self.pomodoro.get_formatted_time(), font_size=48)
        content.add_widget(self.pomodoro_label)
        
        btns = BoxLayout(size_hint_y=None, height=50)
        start_btn = Button(text='Старт')
        start_btn.bind(on_press=lambda x: self.pomodoro.start())
        btns.add_widget(start_btn)
        
        pause_btn = Button(text='Пауза')
        pause_btn.bind(on_press=lambda x: self.pomodoro.pause())
        btns.add_widget(pause_btn)
        
        reset_btn = Button(text='Сброс')
        reset_btn.bind(on_press=lambda x: self.pomodoro.reset())
        btns.add_widget(reset_btn)
        content.add_widget(btns)
        
        Clock.schedule_interval(self.update_pomodoro, 1)
        
        popup.content = content
        popup.open()
        
    def update_pomodoro(self, dt):
        if self.pomodoro.tick():
            self.pomodoro_label.text = self.pomodoro.get_formatted_time()
            if self.pomodoro.time_left == self.pomodoro.work_duration and self.pomodoro.sessions > 0:
                self.show_message('Pomodoro завершен!')
                self.achievements.unlock(5)
                
    def show_todos(self):
        popup = Popup(title='Задачи', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        add_todo = BoxLayout(size_hint_y=None, height=50)
        todo_input = TextInput(hint_text='Новая задача', size_hint_x=0.7)
        add_todo.add_widget(todo_input)
        add_btn = Button(text='+', size_hint_x=0.3)
        add_btn.bind(on_press=lambda x: self.todos.add_todo(todo_input.text))
        add_todo.add_widget(add_btn)
        content.add_widget(add_todo)
        
        for id, text, done, priority in self.todos.get_todos():
            row = BoxLayout(size_hint_y=None, height=40)
            chk = CheckBox(active=bool(done))
            chk.bind(on_press=lambda x, i=id: self.todos.toggle_todo(i))
            row.add_widget(chk)
            row.add_widget(Label(text=text, size_hint_x=0.7))
            del_btn = Button(text='✕', size_hint_x=0.2)
            del_btn.bind(on_press=lambda x, i=id: self.todos.delete_todo(i))
            row.add_widget(del_btn)
            content.add_widget(row)
            
        scroll = ScrollView()
        scroll.add_widget(content)
        popup.content = scroll
        popup.open()
        
    def show_achievements(self):
        popup = Popup(title='Достижения', size_hint=(0.9, 0.7))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        content.add_widget(Label(text=f'Очки: {self.achievements.points}', font_size=24))
        
        unlocked = self.achievements.get_unlocked()
        for name, desc in unlocked:
            content.add_widget(Label(text=f'✓ {name}: {desc}'))
            
        for ach in self.achievements.achievements:
            if ach['name'] not in [u[0] for u in unlocked]:
                content.add_widget(Label(text=f'○ {ach["name"]}: {ach["desc"]} ({ach["points"]} очков)'))
                
        popup.content = content
        popup.open()
        
    def show_games(self):
        popup = Popup(title='Мини-игры', size_hint=(0.8, 0.5))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        for game in self.games.games:
            btn = Button(text=game.capitalize(), size_hint_y=None, height=50)
            content.add_widget(btn)
            
        popup.content = content
        popup.open()
        
    def show_sync(self):
        popup = Popup(title='Синхронизация с ПК', size_hint=(0.9, 0.6))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        content.add_widget(Label(text='Подключитесь к ПК для синхронизации данных'))
        
        ip_section = BoxLayout(size_hint_y=None, height=50)
        ip_section.add_widget(Label(text='IP ПК:', size_hint_x=0.3))
        ip_input = TextInput(hint_text='192.168.1.x', size_hint_x=0.5)
        ip_section.add_widget(ip_input)
        connect_btn = Button(text='Подключить', size_hint_x=0.2)
        ip_section.add_widget(connect_btn)
        content.add_widget(ip_section)
        
        qr_btn = Button(text='📱 Показать QR код', size_hint_y=None, height=50)
        qr_btn.bind(on_press=lambda x: self.show_message('QR код сохранен как sync_qr.png'))
        content.add_widget(qr_btn)
        
        export_btn = Button(text='📤 Экспорт профиля', size_hint_y=None, height=50)
        export_btn.bind(on_press=lambda x: self.sync.export_profile('profile.json'))
        content.add_widget(export_btn)
        
        import_btn = Button(text='📥 Импорт профиля', size_hint_y=None, height=50)
        import_btn.bind(on_press=lambda x: self.show_message('Выберите файл для импорта'))
        content.add_widget(import_btn)
        
        status = self.sync.get_sync_status()
        content.add_widget(Label(text=f'Статус: {"Подключен" if status["connected"] else "Не подключен"}'))
        
        popup.content = content
        popup.open()
        
    def take_screenshot(self, instance=None):
        if self.media.take_screenshot(self.root):
            self.show_message('Скриншот сохранен')
        else:
            self.show_message('Ошибка создания скриншота')
            
    def show_settings(self):
        popup = Popup(title='Настройки', size_hint=(0.9, 0.8))
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        tabs = TabbedPanel()
        
        general = TabbedPanelItem(text='Общие')
        general.content = BoxLayout(orientation='vertical', padding=10)
        general.content.add_widget(Label(text='Домашняя страница:'))
        general.content.add_widget(TextInput(text='https://www.google.com'))
        tabs.add_widget(general)
        
        privacy = TabbedPanelItem(text='Приватность')
        privacy.content = BoxLayout(orientation='vertical', padding=10)
        for name in ['Блокировать куки', 'Не отслеживать', 'Автоудаление истории']:
            row = BoxLayout(size_hint_y=None, height=40)
            row.add_widget(Label(text=name, size_hint_x=0.7))
            row.add_widget(Switch())
            privacy.content.add_widget(row)
        tabs.add_widget(privacy)
        
        security = TabbedPanelItem(text='Безопасность')
        security.content = BoxLayout(orientation='vertical', padding=10)
        security.content.add_widget(Label(text='VirusTotal API ключ:'))
        security.content.add_widget(TextInput(password=True, hint_text='API ключ'))
        security.content.add_widget(Label(text='AI API ключ:'))
        security.content.add_widget(TextInput(password=True, hint_text='API ключ'))
        tabs.add_widget(security)
        
        content.add_widget(tabs)
        popup.content = content
        popup.open()


if __name__ == '__main__':
    BrowserApp().run()
