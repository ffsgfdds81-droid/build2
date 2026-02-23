import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import uuid

DATA_DIR = os.path.expanduser('~/.simple_browser')
NOTES_FILE = os.path.join(DATA_DIR, 'page_notes.json')


class PageNote:
    def __init__(self, content: str, url: str, page_title: str = '',
                 x: int = 0, y: int = 0, color: str = '#FFEB3B'):
        self.id = str(uuid.uuid4())[:8]
        self.content = content
        self.url = url
        self.page_title = page_title
        self.x = x
        self.y = y
        self.color = color
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def update(self, content: str = None, x: int = None, 
               y: int = None, color: str = None):
        if content is not None:
            self.content = content
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if color is not None:
            self.color = color
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'content': self.content,
            'url': self.url,
            'page_title': self.page_title,
            'x': self.x,
            'y': self.y,
            'color': self.color,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PageNote':
        note = cls(
            data.get('content', ''),
            data.get('url', ''),
            data.get('page_title', ''),
            data.get('x', 0),
            data.get('y', 0),
            data.get('color', '#FFEB3B')
        )
        note.id = data.get('id', note.id)
        note.created_at = data.get('created_at', note.created_at)
        note.updated_at = data.get('updated_at', note.updated_at)
        return note


class PageNotesManager:
    def __init__(self):
        self.notes: List[PageNote] = []
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = [PageNote.from_dict(n) for n in data.get('notes', [])]
            except:
                pass
    
    def _save(self):
        data = {
            'notes': [n.to_dict() for n in self.notes]
        }
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_note(self, content: str, url: str, page_title: str = '',
                 x: int = 0, y: int = 0, color: str = '#FFEB3B') -> PageNote:
        note = PageNote(content, url, page_title, x, y, color)
        self.notes.append(note)
        self._save()
        return note
    
    def update_note(self, note_id: str, **kwargs) -> bool:
        note = self.get_note(note_id)
        if not note:
            return False
        
        note.update(**kwargs)
        self._save()
        return True
    
    def delete_note(self, note_id: str) -> bool:
        initial_len = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        if len(self.notes) < initial_len:
            self._save()
            return True
        return False
    
    def get_note(self, note_id: str) -> Optional[PageNote]:
        for note in self.notes:
            if note.id == note_id:
                return note
        return None
    
    def get_notes_for_page(self, url: str) -> List[PageNote]:
        return [n for n in self.notes if n.url == url]
    
    def get_all_notes(self) -> List[PageNote]:
        return sorted(self.notes, key=lambda n: n.created_at, reverse=True)
    
    def search_notes(self, query: str) -> List[PageNote]:
        query = query.lower()
        return [n for n in self.notes if query in n.content.lower()]
    
    def get_notes_count(self) -> int:
        return len(self.notes)
    
    def clear_notes_for_page(self, url: str):
        self.notes = [n for n in self.notes if n.url != url]
        self._save()
    
    def clear_all_notes(self):
        self.notes = []
        self._save()
    
    def get_stats(self) -> Dict:
        pages_with_notes = len(set(n.url for n in self.notes))
        
        return {
            'total_notes': len(self.notes),
            'pages_with_notes': pages_with_notes,
            'oldest_note': self.notes[-1].created_at if self.notes else None,
            'newest_note': self.notes[0].created_at if self.notes else None
        }


class Highlight:
    def __init__(self, text: str, url: str, start: int, end: int,
                 color: str = '#FFEB3B'):
        self.id = str(uuid.uuid4())[:8]
        self.text = text
        self.url = url
        self.start = start
        self.end = end
        self.color = color
        self.note = ''
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'text': self.text,
            'url': self.url,
            'start': self.start,
            'end': self.end,
            'color': self.color,
            'note': self.note,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Highlight':
        h = cls(
            data.get('text', ''),
            data.get('url', ''),
            data.get('start', 0),
            data.get('end', 0),
            data.get('color', '#FFEB3B')
        )
        h.id = data.get('id', h.id)
        h.note = data.get('note', '')
        h.created_at = data.get('created_at', h.created_at)
        return h


class HighlightManager:
    def __init__(self):
        self.highlights: List[Highlight] = []
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        highlight_file = os.path.join(DATA_DIR, 'highlights.json')
        if os.path.exists(highlight_file):
            try:
                with open(highlight_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.highlights = [Highlight.from_dict(h) for h in data.get('highlights', [])]
            except:
                pass
    
    def _save(self):
        highlight_file = os.path.join(DATA_DIR, 'highlights.json')
        data = {
            'highlights': [h.to_dict() for h in self.highlights]
        }
        with open(highlight_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_highlight(self, text: str, url: str, start: int, 
                     end: int, color: str = '#FFEB3B') -> Highlight:
        highlight = Highlight(text, url, start, end, color)
        self.highlights.append(highlight)
        self._save()
        return highlight
    
    def remove_highlight(self, highlight_id: str) -> bool:
        initial_len = len(self.highlights)
        self.highlights = [h for h in self.highlights if h.id != highlight_id]
        if len(self.highlights) < initial_len:
            self._save()
            return True
        return False
    
    def get_highlights_for_page(self, url: str) -> List[Highlight]:
        return [h for h in self.highlights if h.url == url]
    
    def update_highlight_note(self, highlight_id: str, note: str) -> bool:
        for h in self.highlights:
            if h.id == highlight_id:
                h.note = note
                self._save()
                return True
        return False


class Annotation:
    def __init__(self, annotation_type: str, content: str, url: str):
        self.id = str(uuid.uuid4())[:8]
        self.type = annotation_type
        self.content = content
        self.url = url
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'url': self.url,
            'created_at': self.created_at
        }


class AnnotationManager:
    def __init__(self):
        self.annotations: List[Annotation] = []
    
    def add_annotation(self, annotation_type: str, content: str, url: str) -> Annotation:
        annotation = Annotation(annotation_type, content, url)
        self.annotations.append(annotation)
        return annotation
    
    def get_annotations_for_page(self, url: str) -> List[Annotation]:
        return [a for a in self.annotations if a.url == url]
    
    def delete_annotation(self, annotation_id: str) -> bool:
        initial_len = len(self.annotations)
        self.annotations = [a for a in self.annotations if a.id != annotation_id]
        return len(self.annotations) < initial_len
