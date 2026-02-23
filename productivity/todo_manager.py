import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

DATA_DIR = os.path.expanduser('~/.simple_browser')
TODO_FILE = os.path.join(DATA_DIR, 'todos.json')


class TodoPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'


class TodoStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class Todo:
    def __init__(self, text: str, priority: str = 'medium',
                 due_date: str = None, category: str = 'default',
                 tags: List[str] = None):
        self.id = self._generate_id()
        self.text = text
        self.priority = priority
        self.status = TodoStatus.PENDING.value
        self.due_date = due_date
        self.category = category
        self.tags = tags or []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.completed_at = None
        self.subtasks: List[Dict] = []
        self.notes = ''
        self.reminder: Optional[str] = None
        self.repeat: Optional[str] = None
    
    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def complete(self):
        self.status = TodoStatus.COMPLETED.value
        self.completed_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def uncomplete(self):
        self.status = TodoStatus.PENDING.value
        self.completed_at = None
        self.updated_at = datetime.now().isoformat()
    
    def set_priority(self, priority: str):
        self.priority = priority
        self.updated_at = datetime.now().isoformat()
    
    def set_due_date(self, due_date: str):
        self.due_date = due_date
        self.updated_at = datetime.now().isoformat()
    
    def add_subtask(self, text: str) -> Dict:
        subtask = {
            'id': self._generate_id(),
            'text': text,
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        self.subtasks.append(subtask)
        self.updated_at = datetime.now().isoformat()
        return subtask
    
    def complete_subtask(self, subtask_id: str) -> bool:
        for subtask in self.subtasks:
            if subtask['id'] == subtask_id:
                subtask['completed'] = True
                self.updated_at = datetime.now().isoformat()
                return True
        return False
    
    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now().isoformat()
    
    def remove_tag(self, tag: str) -> bool:
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        if self.status == TodoStatus.COMPLETED.value:
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            return due < datetime.now()
        except:
            return False
    
    def get_progress(self) -> float:
        if not self.subtasks:
            return 0 if self.status != TodoStatus.COMPLETED.value else 100
        completed = sum(1 for s in self.subtasks if s['completed'])
        return (completed / len(self.subtasks)) * 100
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'text': self.text,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date,
            'category': self.category,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at,
            'subtasks': self.subtasks,
            'notes': self.notes,
            'reminder': self.reminder,
            'repeat': self.repeat
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Todo':
        todo = cls(data['text'], data.get('priority', 'medium'),
                  data.get('due_date'), data.get('category', 'default'),
                  data.get('tags', []))
        todo.id = data.get('id', todo.id)
        todo.status = data.get('status', TodoStatus.PENDING.value)
        todo.created_at = data.get('created_at', todo.created_at)
        todo.updated_at = data.get('updated_at', todo.updated_at)
        todo.completed_at = data.get('completed_at')
        todo.subtasks = data.get('subtasks', [])
        todo.notes = data.get('notes', '')
        todo.reminder = data.get('reminder')
        todo.repeat = data.get('repeat')
        return todo


class TodoManager:
    def __init__(self):
        self.todos: List[Todo] = []
        self.categories = ['default', 'work', 'personal', 'shopping', 'health']
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(TODO_FILE):
            try:
                with open(TODO_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todos = [Todo.from_dict(t) for t in data.get('todos', [])]
                    self.categories = data.get('categories', self.categories)
            except:
                pass
    
    def _save(self):
        data = {
            'todos': [t.to_dict() for t in self.todos],
            'categories': self.categories
        }
        with open(TODO_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add(self, text: str, priority: str = 'medium',
            due_date: str = None, category: str = 'default',
            tags: List[str] = None) -> Todo:
        todo = Todo(text, priority, due_date, category, tags)
        self.todos.append(todo)
        self._save()
        return todo
    
    def remove(self, todo_id: str) -> bool:
        initial_len = len(self.todos)
        self.todos = [t for t in self.todos if t.id != todo_id]
        if len(self.todos) < initial_len:
            self._save()
            return True
        return False
    
    def get(self, todo_id: str) -> Optional[Todo]:
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def complete(self, todo_id: str) -> bool:
        todo = self.get(todo_id)
        if todo:
            todo.complete()
            self._save()
            return True
        return False
    
    def uncomplete(self, todo_id: str) -> bool:
        todo = self.get(todo_id)
        if todo:
            todo.uncomplete()
            self._save()
            return True
        return False
    
    def update(self, todo_id: str, **kwargs) -> bool:
        todo = self.get(todo_id)
        if not todo:
            return False
        
        for key, value in kwargs.items():
            if hasattr(todo, key):
                setattr(todo, key, value)
        
        todo.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def get_all(self) -> List[Todo]:
        return self.todos
    
    def get_pending(self) -> List[Todo]:
        return [t for t in self.todos if t.status != TodoStatus.COMPLETED.value]
    
    def get_completed(self) -> List[Todo]:
        return [t for t in self.todos if t.status == TodoStatus.COMPLETED.value]
    
    def get_by_category(self, category: str) -> List[Todo]:
        return [t for t in self.todos if t.category == category]
    
    def get_by_priority(self, priority: str) -> List[Todo]:
        return [t for t in self.todos if t.priority == priority]
    
    def get_due_today(self) -> List[Todo]:
        today = datetime.now().date().isoformat()
        return [t for t in self.todos if t.due_date and t.due_date.startswith(today)]
    
    def get_overdue(self) -> List[Todo]:
        return [t for t in self.todos if t.is_overdue()]
    
    def get_by_tag(self, tag: str) -> List[Todo]:
        return [t for t in self.todos if tag in t.tags]
    
    def search(self, query: str) -> List[Todo]:
        query = query.lower()
        return [t for t in self.todos
                if query in t.text.lower() or query in t.notes.lower()]
    
    def sort_by_priority(self, todos: List[Todo] = None) -> List[Todo]:
        if todos is None:
            todos = self.todos
        
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        return sorted(todos, key=lambda t: priority_order.get(t.priority, 2))
    
    def sort_by_due_date(self, todos: List[Todo] = None) -> List[Todo]:
        if todos is None:
            todos = self.todos
        
        return sorted(todos, key=lambda t: (t.due_date is None, t.due_date or ''))
    
    def get_stats(self) -> Dict:
        total = len(self.todos)
        completed = len([t for t in self.todos if t.status == TodoStatus.COMPLETED.value])
        pending = total - completed
        overdue = len(self.get_overdue())
        
        by_priority = {
            'urgent': len(self.get_by_priority('urgent')),
            'high': len(self.get_by_priority('high')),
            'medium': len(self.get_by_priority('medium')),
            'low': len(self.get_by_priority('low'))
        }
        
        by_category = {}
        for cat in self.categories:
            by_category[cat] = len(self.get_by_category(cat))
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'overdue': overdue,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1),
            'by_priority': by_priority,
            'by_category': by_category
        }
    
    def add_category(self, category: str):
        if category not in self.categories:
            self.categories.append(category)
            self._save()
    
    def remove_category(self, category: str) -> bool:
        if category in self.categories and category != 'default':
            self.categories.remove(category)
            for todo in self.todos:
                if todo.category == category:
                    todo.category = 'default'
            self._save()
            return True
        return False
    
    def clear_completed(self):
        self.todos = [t for t in self.todos if t.status != TodoStatus.COMPLETED.value]
        self._save()
    
    def clear_all(self):
        self.todos = []
        self._save()
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'priority', 'status', 'due_date', 'category', 'tags', 'created_at'])
            for t in self.todos:
                writer.writerow([
                    t.text, t.priority, t.status, t.due_date or '',
                    t.category, ','.join(t.tags), t.created_at
                ])
    
    def import_csv(self, filepath: str):
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add(
                    row['text'],
                    row.get('priority', 'medium'),
                    row.get('due_date'),
                    row.get('category', 'default'),
                    row.get('tags', '').split(',') if row.get('tags') else []
                )


class TodoReminder:
    def __init__(self, todo_manager: TodoManager):
        self.todo_manager = todo_manager
        self.callbacks = []
    
    def check_reminders(self) -> List[Todo]:
        now = datetime.now()
        due_reminders = []
        
        for todo in self.todo_manager.get_pending():
            if todo.due_date and todo.reminder:
                try:
                    due_dt = datetime.fromisoformat(todo.due_date)
                    reminder_dt = due_dt - timedelta(minutes=int(todo.reminder))
                    
                    if now >= reminder_dt and now < due_dt:
                        due_reminders.append(todo)
                except:
                    pass
        
        return due_reminders
    
    def on_reminder(self, callback):
        self.callbacks.append(callback)
    
    def notify(self, todo: Todo):
        for callback in self.callbacks:
            try:
                callback(todo)
            except:
                pass
