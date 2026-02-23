import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

DATA_DIR = os.path.expanduser('~/.simple_browser')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')


class HistoryEntry:
    def __init__(self, url: str, title: str, visit_count: int = 1,
                 last_visit: str = None, favicon: str = ''):
        self.url = url
        self.title = title
        self.visit_count = visit_count
        self.last_visit = last_visit or datetime.now().isoformat()
        self.favicon = favicon
        self.first_visit = last_visit or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'visit_count': self.visit_count,
            'last_visit': self.last_visit,
            'first_visit': self.first_visit,
            'favicon': self.favicon
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HistoryEntry':
        entry = cls(
            data['url'], data['title'], data.get('visit_count', 1),
            data.get('last_visit'), data.get('favicon', '')
        )
        entry.first_visit = data.get('first_visit', entry.first_visit)
        return entry


class HistoryManager:
    def __init__(self, max_entries: int = 10000):
        self.history: List[HistoryEntry] = []
        self.max_entries = max_entries
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [HistoryEntry.from_dict(h) for h in data.get('history', [])]
            except:
                self.history = []
    
    def _save(self):
        data = {'history': [h.to_dict() for h in self.history]}
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add(self, url: str, title: str = '', favicon: str = ''):
        for entry in self.history:
            if entry.url == url:
                entry.visit_count += 1
                entry.last_visit = datetime.now().isoformat()
                entry.title = title or entry.title
                self.history.remove(entry)
                self.history.insert(0, entry)
                self._save()
                return
        
        entry = HistoryEntry(url, title or url, favicon=favicon)
        self.history.insert(0, entry)
        
        if len(self.history) > self.max_entries:
            self.history = self.history[:self.max_entries]
        
        self._save()
    
    def remove(self, url: str) -> bool:
        initial_len = len(self.history)
        self.history = [h for h in self.history if h.url != url]
        if len(self.history) < initial_len:
            self._save()
            return True
        return False
    
    def clear(self):
        self.history = []
        self._save()
    
    def get_all(self, limit: int = 100) -> List[HistoryEntry]:
        return self.history[:limit]
    
    def search(self, query: str, limit: int = 50) -> List[HistoryEntry]:
        query = query.lower()
        return [h for h in self.history 
                if query in h.title.lower() or query in h.url.lower()][:limit]
    
    def get_most_visited(self, limit: int = 20) -> List[HistoryEntry]:
        return sorted(self.history, key=lambda x: x.visit_count, reverse=True)[:limit]
    
    def get_by_date(self, date: datetime) -> List[HistoryEntry]:
        date_str = date.date().isoformat()
        return [h for h in self.history if h.last_visit.startswith(date_str)]
    
    def get_today(self) -> List[HistoryEntry]:
        return self.get_by_date(datetime.now())
    
    def get_yesterday(self) -> List[HistoryEntry]:
        return self.get_by_date(datetime.now() - timedelta(days=1))
    
    def get_last_week(self) -> List[HistoryEntry]:
        week_ago = datetime.now() - timedelta(days=7)
        return [h for h in self.history 
                if datetime.fromisoformat(h.last_visit) > week_ago]
    
    def get_domain_stats(self) -> Dict[str, int]:
        stats = defaultdict(int)
        for entry in self.history:
            domain = entry.url.split('/')[2] if '/' in entry.url else entry.url
            stats[domain] += entry.visit_count
        return dict(stats)
    
    def get_daily_stats(self, days: int = 7) -> Dict[str, int]:
        stats = defaultdict(int)
        for entry in self.history:
            date = entry.last_visit.split('T')[0]
            stats[date] += 1
        
        result = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            result[date] = stats.get(date, 0)
        
        return result
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'url', 'visit_count', 'last_visit', 'first_visit'])
            for h in self.history:
                writer.writerow([h.title, h.url, h.visit_count, h.last_visit, h.first_visit])
    
    def import_csv(self, filepath: str):
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add(row['url'], row['title'])
