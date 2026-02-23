import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DATA_DIR = os.path.expanduser('~/.simple_browser')
BOOKMARKS_FILE = os.path.join(DATA_DIR, 'bookmarks.json')


class Bookmark:
    def __init__(self, url: str, title: str, folder: str = 'default', 
                 favicon: str = '', created_at: str = None):
        self.url = url
        self.title = title
        self.folder = folder
        self.favicon = favicon
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'folder': self.folder,
            'favicon': self.favicon,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bookmark':
        return cls(**data)


class BookmarkManager:
    def __init__(self):
        self.bookmarks: List[Bookmark] = []
        self.folders = {'default': 'Default', 'work': 'Work', 'personal': 'Personal'}
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(BOOKMARKS_FILE):
            try:
                with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.bookmarks = [Bookmark.from_dict(b) for b in data.get('bookmarks', [])]
                    self.folders = data.get('folders', self.folders)
            except:
                self.bookmarks = []
    
    def _save(self):
        data = {
            'bookmarks': [b.to_dict() for b in self.bookmarks],
            'folders': self.folders
        }
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add(self, url: str, title: str, folder: str = 'default', favicon: str = '') -> Bookmark:
        bookmark = Bookmark(url, title, folder, favicon)
        self.bookmarks.insert(0, bookmark)
        self._save()
        return bookmark
    
    def remove(self, url: str) -> bool:
        initial_len = len(self.bookmarks)
        self.bookmarks = [b for b in self.bookmarks if b.url != url]
        if len(self.bookmarks) < initial_len:
            self._save()
            return True
        return False
    
    def get_all(self) -> List[Bookmark]:
        return self.bookmarks
    
    def get_by_folder(self, folder: str) -> List[Bookmark]:
        return [b for b in self.bookmarks if b.folder == folder]
    
    def search(self, query: str) -> List[Bookmark]:
        query = query.lower()
        return [b for b in self.bookmarks 
                if query in b.title.lower() or query in b.url.lower()]
    
    def is_bookmarked(self, url: str) -> bool:
        return any(b.url == url for b in self.bookmarks)
    
    def add_folder(self, name: str, display_name: str = None):
        if name not in self.folders:
            self.folders[name] = display_name or name
            self._save()
    
    def remove_folder(self, name: str):
        if name in self.folders and name != 'default':
            del self.folders[name]
            for b in self.bookmarks:
                if b.folder == name:
                    b.folder = 'default'
            self._save()
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'url', 'folder', 'created_at'])
            for b in self.bookmarks:
                writer.writerow([b.title, b.url, b.folder, b.created_at])
    
    def import_csv(self, filepath: str):
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add(row['url'], row['title'], row.get('folder', 'default'))
    
    def get_folders(self) -> Dict[str, str]:
        return self.folders
