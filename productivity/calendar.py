import json
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from enum import Enum

DATA_DIR = os.path.expanduser('~/.simple_browser')
CALENDAR_FILE = os.path.join(DATA_DIR, 'calendar.json')


class EventType(Enum):
    EVENT = 'event'
    REMINDER = 'reminder'
    TASK = 'task'
    BIRTHDAY = 'birthday'
    ANNIVERSARY = 'anniversary'


class CalendarEvent:
    def __init__(self, title: str, description: str = '',
                 start_time: str = None, end_time: str = None,
                 all_day: bool = False, event_type: str = 'event',
                 location: str = '', color: str = '#2196F3'):
        self.id = self._generate_id()
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.all_day = all_day
        self.event_type = event_type
        self.location = location
        self.color = color
        self.recurrence: Optional[str] = None
        self.reminder: Optional[int] = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def get_date(self) -> str:
        if self.start_time:
            return self.start_time.split('T')[0]
        return datetime.now().date().isoformat()
    
    def is_recurring(self) -> bool:
        return self.recurrence is not None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'all_day': self.all_day,
            'event_type': self.event_type,
            'location': self.location,
            'color': self.color,
            'recurrence': self.recurrence,
            'reminder': self.reminder,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CalendarEvent':
        event = cls(
            data['title'], data.get('description', ''),
            data.get('start_time'), data.get('end_time'),
            data.get('all_day', False), data.get('event_type', 'event'),
            data.get('location', ''), data.get('color', '#2196F3')
        )
        event.id = data.get('id', event.id)
        event.recurrence = data.get('recurrence')
        event.reminder = data.get('reminder')
        event.created_at = data.get('created_at', event.created_at)
        event.updated_at = data.get('updated_at', event.updated_at)
        return event


class CalendarNote:
    def __init__(self, content: str, date: str = None):
        self.id = self._generate_id()
        self.content = content
        self.date = date or datetime.now().date().isoformat()
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'content': self.content,
            'date': self.date,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CalendarNote':
        note = cls(data['content'], data.get('date'))
        note.id = data.get('id', note.id)
        note.created_at = data.get('created_at', note.created_at)
        note.updated_at = data.get('updated_at', note.updated_at)
        return note


class Calendar:
    def __init__(self):
        self.events: List[CalendarEvent] = []
        self.notes: List[CalendarNote] = []
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(CALENDAR_FILE):
            try:
                with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events = [CalendarEvent.from_dict(e) for e in data.get('events', [])]
                    self.notes = [CalendarNote.from_dict(n) for n in data.get('notes', [])]
            except:
                pass
    
    def _save(self):
        data = {
            'events': [e.to_dict() for e in self.events],
            'notes': [n.to_dict() for n in self.notes]
        }
        with open(CALENDAR_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_event(self, title: str, description: str = '',
                  start_time: str = None, end_time: str = None,
                  all_day: bool = False, event_type: str = 'event',
                  location: str = '', color: str = '#2196F3',
                  recurrence: str = None, reminder: int = None) -> CalendarEvent:
        event = CalendarEvent(title, description, start_time, end_time,
                            all_day, event_type, location, color)
        event.recurrence = recurrence
        event.reminder = reminder
        self.events.append(event)
        self._save()
        return event
    
    def remove_event(self, event_id: str) -> bool:
        initial_len = len(self.events)
        self.events = [e for e in self.events if e.id != event_id]
        if len(self.events) < initial_len:
            self._save()
            return True
        return False
    
    def update_event(self, event_id: str, **kwargs) -> bool:
        event = self.get_event(event_id)
        if not event:
            return False
        
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        event.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        for event in self.events:
            if event.id == event_id:
                return event
        return None
    
    def get_events_by_date(self, date: str) -> List[CalendarEvent]:
        return [e for e in self.events if e.get_date() == date]
    
    def get_events_by_range(self, start: str, end: str) -> List[CalendarEvent]:
        return [e for e in self.events 
                if e.start_time and start <= e.get_date() <= end]
    
    def get_today_events(self) -> List[CalendarEvent]:
        today = datetime.now().date().isoformat()
        return self.get_events_by_date(today)
    
    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        today = datetime.now().date()
        end = today + timedelta(days=days)
        return self.get_events_by_range(today.isoformat(), end.isoformat())
    
    def add_note(self, content: str, date: str = None) -> CalendarNote:
        note = CalendarNote(content, date)
        self.notes.append(note)
        self._save()
        return note
    
    def remove_note(self, note_id: str) -> bool:
        initial_len = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        if len(self.notes) < initial_len:
            self._save()
            return True
        return False
    
    def get_notes_by_date(self, date: str) -> List[CalendarNote]:
        return [n for n in self.notes if n.date == date]
    
    def get_all_notes(self) -> List[CalendarNote]:
        return sorted(self.notes, key=lambda n: n.date, reverse=True)
    
    def search_notes(self, query: str) -> List[CalendarNote]:
        query = query.lower()
        return [n for n in self.notes if query in n.content.lower()]
    
    def get_calendar_days(self, year: int, month: int) -> Dict[str, Dict]:
        first_day = date(year, month, 1)
        last_day = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year + 1, 1, 1) - timedelta(days=1)
        
        days = {}
        
        current = first_day
        while current <= last_day:
            day_str = current.isoformat()
            events = self.get_events_by_date(day_str)
            notes = self.get_notes_by_date(day_str)
            
            days[day_str] = {
                'events': events,
                'notes': notes,
                'has_events': len(events) > 0,
                'has_notes': len(notes) > 0,
                'is_today': current == datetime.now().date()
            }
            
            current += timedelta(days=1)
        
        return days
    
    def get_stats(self) -> Dict:
        today = datetime.now().date().isoformat()
        
        total_events = len(self.events)
        total_notes = len(self.notes)
        
        today_events = len(self.get_today_events())
        upcoming = len(self.get_upcoming_events())
        
        event_types = {}
        for event in self.events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        return {
            'total_events': total_events,
            'total_notes': total_notes,
            'today_events': today_events,
            'upcoming_events': upcoming,
            'event_types': event_types
        }
    
    def export_ics(self, filepath: str):
        import re
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('BEGIN:VCALENDAR\n')
            f.write('VERSION:2.0\n')
            f.write('PRODID:-//Simple Browser//Calendar//EN\n')
            
            for event in self.events:
                f.write('BEGIN:VEVENT\n')
                f.write(f'UID:{event.id}@simplebrowser\n')
                f.write(f'DTSTART:{event.start_time.replace("-", "").replace(":", "")}\n')
                if event.end_time:
                    f.write(f'DTEND:{event.end_time.replace("-", "").replace(":", "")}\n')
                f.write(f'SUMMARY:{event.title}\n')
                if event.description:
                    f.write(f'DESCRIPTION:{event.description}\n')
                f.write('END:VEVENT\n')
            
            f.write('END:VCALENDAR\n')
    
    def import_ics(self, filepath: str):
        import re
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            events = re.split(r'BEGIN:VEVENT', content)[1:]
            
            for event_data in events:
                title_match = re.search(r'SUMMARY:(.+?)(?:\n|$)', event_data)
                start_match = re.search(r'DTSTART(?:;.*?)?:(.+?)(?:\n|$)', event_data)
                
                if title_match and start_match:
                    title = title_match.group(1)
                    start = start_match.group(1)
                    
                    if len(start) == 8:
                        start = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
                    
                    self.add_event(title, start_time=start)
        except:
            pass


class CalendarView:
    @staticmethod
    def get_month_name(month: int) -> str:
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[month - 1] if 1 <= month <= 12 else ''
    
    @staticmethod
    def get_day_name(day: int) -> str:
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return days[day - 1] if 1 <= day <= 7 else ''
    
    @staticmethod
    def format_event_time(event: CalendarEvent) -> str:
        if event.all_day:
            return 'All Day'
        
        if event.start_time:
            try:
                dt = datetime.fromisoformat(event.start_time)
                return dt.strftime('%H:%M')
            except:
                pass
        
        return ''
    
    @staticmethod
    def get_color_for_type(event_type: str) -> str:
        colors = {
            'event': '#2196F3',
            'reminder': '#FF9800',
            'task': '#4CAF50',
            'birthday': '#E91E63',
            'anniversary': '#9C27B0'
        }
        return colors.get(event_type, '#2196F3')
