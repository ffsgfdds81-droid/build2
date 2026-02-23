import uuid
from datetime import datetime
from typing import List, Dict, Optional


class Tab:
    def __init__(self, url: str = 'about:blank', title: str = 'New Tab',
                 favicon: str = '', is_pinned: bool = False):
        self.id = str(uuid.uuid4())
        self.url = url
        self.title = title
        self.favicon = favicon
        self.is_pinned = is_pinned
        self.created_at = datetime.now().isoformat()
        self.last_active = datetime.now().isoformat()
        self.screenshot = None
        self.is_loading = False
        self.scroll_position = 0
    
    def update(self, url: str = None, title: str = None, favicon: str = None):
        if url is not None:
            self.url = url
        if title is not None:
            self.title = title
        if favicon is not None:
            self.favicon = favicon
        self.last_active = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'favicon': self.favicon,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at,
            'last_active': self.last_active,
            'scroll_position': self.scroll_position
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tab':
        tab = cls(data['url'], data['title'], data.get('favicon', ''),
                 data.get('is_pinned', False))
        tab.id = data['id']
        tab.created_at = data.get('created_at', tab.created_at)
        tab.last_active = data.get('last_active', tab.last_active)
        tab.scroll_position = data.get('scroll_position', 0)
        return tab


class TabGroup:
    def __init__(self, name: str, color: str = '#808080'):
        self.id = str(uuid.uuid4())
        self.name = name
        self.color = color
        self.tab_ids: List[str] = []
        self.created_at = datetime.now().isoformat()
    
    def add_tab(self, tab_id: str):
        if tab_id not in self.tab_ids:
            self.tab_ids.append(tab_id)
    
    def remove_tab(self, tab_id: str):
        if tab_id in self.tab_ids:
            self.tab_ids.remove(tab_id)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'tab_ids': self.tab_ids,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TabGroup':
        group = cls(data['name'], data.get('color', '#808080'))
        group.id = data['id']
        group.tab_ids = data.get('tab_ids', [])
        group.created_at = data.get('created_at', group.created_at)
        return group


class TabManager:
    def __init__(self):
        self.tabs: List[Tab] = []
        self.active_tab_id: Optional[str] = None
        self.groups: List[TabGroup] = []
        self.max_tabs = 50
    
    def create_tab(self, url: str = 'about:blank', title: str = 'New Tab',
                   favicon: str = '', activate: bool = True) -> Tab:
        if len(self.tabs) >= self.max_tabs:
            self.close_inactive_tabs()
        
        tab = Tab(url, title, favicon)
        self.tabs.append(tab)
        
        if activate or not self.active_tab_id:
            self.active_tab_id = tab.id
        
        return tab
    
    def close_tab(self, tab_id: str) -> bool:
        for i, tab in enumerate(self.tabs):
            if tab.id == tab_id:
                self.tabs.pop(i)
                
                if self.active_tab_id == tab_id:
                    if i > 0:
                        self.active_tab_id = self.tabs[i - 1].id
                    elif self.tabs:
                        self.active_tab_id = self.tabs[0].id
                    else:
                        self.active_tab_id = None
                
                return True
        return False
    
    def get_active_tab(self) -> Optional[Tab]:
        if not self.active_tab_id:
            return None
        for tab in self.tabs:
            if tab.id == self.active_tab_id:
                return tab
        return None
    
    def set_active_tab(self, tab_id: str) -> bool:
        for tab in self.tabs:
            if tab.id == tab_id:
                self.active_tab_id = tab_id
                tab.last_active = datetime.now().isoformat()
                return True
        return False
    
    def get_tab(self, tab_id: str) -> Optional[Tab]:
        for tab in self.tabs:
            if tab.id == tab_id:
                return tab
        return None
    
    def get_all_tabs(self) -> List[Tab]:
        return self.tabs
    
    def get_pinned_tabs(self) -> List[Tab]:
        return [t for t in self.tabs if t.is_pinned]
    
    def get_unpinned_tabs(self) -> List[Tab]:
        return [t for t in self.tabs if not t.is_pinned]
    
    def pin_tab(self, tab_id: str) -> bool:
        for tab in self.tabs:
            if tab.id == tab_id:
                tab.is_pinned = True
                return True
        return False
    
    def unpin_tab(self, tab_id: str) -> bool:
        for tab in self.tabs:
            if tab.id == tab_id:
                tab.is_pinned = False
                return True
        return False
    
    def duplicate_tab(self, tab_id: str) -> Optional[Tab]:
        tab = self.get_tab(tab_id)
        if tab:
            return self.create_tab(tab.url, tab.title, tab.favicon)
        return None
    
    def move_tab(self, tab_id: str, new_index: int) -> bool:
        for i, tab in enumerate(self.tabs):
            if tab.id == tab_id:
                if 0 <= new_index < len(self.tabs):
                    self.tabs.pop(i)
                    self.tabs.insert(new_index, tab)
                    return True
        return False
    
    def close_inactive_tabs(self):
        active = self.get_active_tab()
        if active:
            self.tabs = [active]
    
    def close_all_tabs(self, keep_pinned: bool = False):
        if keep_pinned:
            self.tabs = self.get_pinned_tabs()
        else:
            self.tabs = []
        self.active_tab_id = None
    
    def search_tabs(self, query: str) -> List[Tab]:
        query = query.lower()
        return [t for t in self.tabs 
                if query in t.title.lower() or query in t.url.lower()]
    
    def create_group(self, name: str, color: str = '#808080') -> TabGroup:
        group = TabGroup(name, color)
        self.groups.append(group)
        return group
    
    def add_to_group(self, tab_id: str, group_id: str) -> bool:
        for group in self.groups:
            if group.id == group_id:
                group.add_tab(tab_id)
                return True
        return False
    
    def remove_from_group(self, tab_id: str) -> bool:
        for group in self.groups:
            group.remove_tab(tab_id)
        return True
    
    def get_group_tabs(self, group_id: str) -> List[Tab]:
        for group in self.groups:
            if group.id == group_id:
                return [t for t in self.tabs if t.id in group.tab_ids]
        return []
    
    def close_group_tabs(self, group_id: str):
        for group in self.groups:
            if group.id == group_id:
                for tab_id in group.tab_ids[:]:
                    self.close_tab(tab_id)
                group.tab_ids = []
                return
    
    def delete_group(self, group_id: str) -> bool:
        for i, group in enumerate(self.groups):
            if group.id == group_id:
                self.groups.pop(i)
                return True
        return False
    
    def get_tab_count(self) -> int:
        return len(self.tabs)
    
    def to_dict(self) -> dict:
        return {
            'tabs': [t.to_dict() for t in self.tabs],
            'active_tab_id': self.active_tab_id,
            'groups': [g.to_dict() for g in self.groups]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TabManager':
        manager = cls()
        manager.tabs = [Tab.from_dict(t) for t in data.get('tabs', [])]
        manager.active_tab_id = data.get('active_tab_id')
        manager.groups = [TabGroup.from_dict(g) for g in data.get('groups', [])]
        return manager
