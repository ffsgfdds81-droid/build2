import json
import os
import hashlib
import base64
import secrets
import string
from datetime import datetime
from typing import List, Dict, Optional

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

DATA_DIR = os.path.expanduser('~/.simple_browser')
PASSWORDS_FILE = os.path.join(DATA_DIR, 'passwords.enc')
MASTER_FILE = os.path.join(DATA_DIR, 'master.hash')


class PasswordEntry:
    def __init__(self, site: str, username: str, password: str, 
                 notes: str = '', created_at: str = None, modified_at: str = None,
                 favicon: str = '', category: str = 'default'):
        self.site = site
        self.username = username
        self.password = password
        self.notes = notes
        self.created_at = created_at or datetime.now().isoformat()
        self.modified_at = modified_at or datetime.now().isoformat()
        self.favicon = favicon
        self.category = category
    
    def to_dict(self) -> dict:
        return {
            'site': self.site,
            'username': self.username,
            'password': self.password,
            'notes': self.notes,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'favicon': self.favicon,
            'category': self.category
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PasswordEntry':
        return cls(**data)


class PasswordManager:
    def __init__(self):
        self.master_password = None
        self.cipher = None
        self.passwords: List[PasswordEntry] = []
        self.categories = ['default', 'work', 'social', 'finance', 'shopping']
        self._load_master()
        self._load_passwords()
    
    def _load_master(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, 'r') as f:
                self.master_hash = f.read().strip()
        else:
            self.master_hash = None
    
    def _load_passwords(self):
        if not os.path.exists(PASSWORDS_FILE):
            return
        
        if not CRYPTO_AVAILABLE:
            return
        
        try:
            with open(PASSWORDS_FILE, 'rb') as f:
                encrypted_data = f.read()
            
            if self.cipher and encrypted_data:
                decrypted = self.cipher.decrypt(encrypted_data)
                data = json.loads(decrypted)
                self.passwords = [PasswordEntry.from_dict(p) for p in data]
        except:
            pass
    
    def _save_passwords(self):
        if not CRYPTO_AVAILABLE or not self.cipher:
            return
        
        data = json.dumps([p.to_dict() for p in self.passwords])
        encrypted = self.cipher.encrypt(data.encode())
        
        with open(PASSWORDS_FILE, 'wb') as f:
            f.write(encrypted)
    
    def set_master_password(self, password: str) -> bool:
        if not CRYPTO_AVAILABLE:
            return False
        
        self.master_password = password
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000)
        )
        self.cipher = Fernet(key)
        
        self.master_hash = hashlib.sha256(password.encode()).hexdigest()
        with open(MASTER_FILE, 'w') as f:
            f.write(self.master_hash)
        
        self._save_passwords()
        return True
    
    def unlock(self, password: str) -> bool:
        if not CRYPTO_AVAILABLE:
            return False
        
        if not self.master_hash:
            return False
        
        if hashlib.sha256(password.encode()).hexdigest() != self.master_hash:
            return False
        
        self.master_password = password
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000)
        )
        self.cipher = Fernet(key)
        self._load_passwords()
        return True
    
    def is_locked(self) -> bool:
        return self.cipher is None
    
    def is_first_time(self) -> bool:
        return self.master_hash is None
    
    def lock(self):
        self.cipher = None
        self.master_password = None
        self.passwords = []
    
    def add(self, site: str, username: str, password: str, 
            notes: str = '', category: str = 'default') -> PasswordEntry:
        entry = PasswordEntry(site, username, password, notes, category=category)
        self.passwords.insert(0, entry)
        self._save_passwords()
        return entry
    
    def update(self, site: str, username: str = None, password: str = None,
               notes: str = None, category: str = None) -> bool:
        for entry in self.passwords:
            if entry.site == site:
                if username:
                    entry.username = username
                if password:
                    entry.password = password
                if notes is not None:
                    entry.notes = notes
                if category:
                    entry.category = category
                entry.modified_at = datetime.now().isoformat()
                self._save_passwords()
                return True
        return False
    
    def remove(self, site: str) -> bool:
        initial_len = len(self.passwords)
        self.passwords = [p for p in self.passwords if p.site != site]
        if len(self.passwords) < initial_len:
            self._save_passwords()
            return True
        return False
    
    def get(self, site: str) -> Optional[PasswordEntry]:
        for entry in self.passwords:
            if entry.site == site:
                return entry
        return None
    
    def get_all(self) -> List[PasswordEntry]:
        return self.passwords
    
    def get_by_category(self, category: str) -> List[PasswordEntry]:
        return [p for p in self.passwords if p.category == category]
    
    def search(self, query: str) -> List[PasswordEntry]:
        query = query.lower()
        return [p for p in self.passwords 
                if query in p.site.lower() or query in p.username.lower()]
    
    def generate_password(self, length: int = 16, 
                         use_uppercase: bool = True,
                         use_lowercase: bool = True,
                         use_numbers: bool = True,
                         use_special: bool = True) -> str:
        chars = ''
        if use_lowercase:
            chars += string.ascii_lowercase
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_numbers:
            chars += string.digits
        if use_special:
            chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        if not chars:
            chars = string.ascii_letters + string.digits
        
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def check_password_strength(self, password: str) -> Dict[str, any]:
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            score += 1
        
        if score < 3:
            strength = 'weak'
        elif score < 5:
            strength = 'medium'
        elif score < 7:
            strength = 'strong'
        else:
            strength = 'very_strong'
        
        if len(password) < 8:
            feedback.append('Use at least 8 characters')
        if not any(c.isupper() for c in password):
            feedback.append('Add uppercase letters')
        if not any(c.isdigit() for c in password):
            feedback.append('Add numbers')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            feedback.append('Add special characters')
        
        return {
            'score': score,
            'strength': strength,
            'feedback': feedback
        }
    
    def export_csv(self, filepath: str, include_passwords: bool = False):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if include_passwords:
                writer.writerow(['site', 'username', 'password', 'notes', 'category', 'created_at'])
                for p in self.passwords:
                    writer.writerow([p.site, p.username, p.password, p.notes, 
                                   p.category, p.created_at])
            else:
                writer.writerow(['site', 'username', 'notes', 'category', 'created_at'])
                for p in self.passwords:
                    writer.writerow([p.site, p.username, p.notes, p.category, p.created_at])
    
    def import_csv(self, filepath: str):
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'password' in row and row['password']:
                    self.add(row['site'], row['username'], row['password'],
                           row.get('notes', ''), row.get('category', 'default'))
    
    def get_categories(self) -> List[str]:
        return self.categories
    
    def add_category(self, category: str):
        if category not in self.categories:
            self.categories.append(category)
    
    def remove_category(self, category: str):
        if category in self.categories and category != 'default':
            self.categories.remove(category)
            for p in self.passwords:
                if p.category == category:
                    p.category = 'default'
            self._save_passwords()
