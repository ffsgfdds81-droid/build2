import socket
import threading
import time
import random
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser('~/.simple_browser')
PROXY_FILE = os.path.join(DATA_DIR, 'proxies.json')


class ProxyServer:
    def __init__(self, host: str, port: int, protocol: str = 'http',
                 country: str = '', username: str = '', password: str = ''):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.country = country
        self.username = username
        self.password = password
        self.latency = 0
        self.last_checked = None
        self.working = True
        self.failures = 0
    
    def check_latency(self) -> int:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            sock.close()
            latency = int((time.time() - start) * 1000)
            self.latency = latency
            self.last_checked = datetime.now()
            self.working = True
            return latency
        except:
            self.working = False
            self.failures += 1
            return -1
    
    def to_dict(self) -> dict:
        return {
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'country': self.country,
            'username': self.username,
            'password': self.password,
            'latency': self.latency,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'working': self.working
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProxyServer':
        proxy = cls(
            data['host'], data['port'], data.get('protocol', 'http'),
            data.get('country', ''), data.get('username', ''),
            data.get('password', '')
        )
        proxy.latency = data.get('latency', 0)
        proxy.working = data.get('working', True)
        if data.get('last_checked'):
            proxy.last_checked = datetime.fromisoformat(data['last_checked'])
        return proxy


class ProxyManager:
    def __init__(self):
        self.proxies: List[ProxyServer] = []
        self.current_proxy: Optional[ProxyServer] = None
        self.enabled = False
        self.rotation_mode = 'sequential'
        self.auto_rotate = False
        self.rotate_interval = 300
        self.last_rotation = None
        self._load_default_proxies()
        self._load()
    
    def _load_default_proxies(self):
        pass
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(PROXY_FILE):
            try:
                with open(PROXY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.proxies = [ProxyServer.from_dict(p) for p in data.get('proxies', [])]
            except:
                pass
    
    def _save(self):
        data = {'proxies': [p.to_dict() for p in self.proxies]}
        with open(PROXY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_proxy(self, host: str, port: int, protocol: str = 'http',
                  country: str = '', username: str = '', password: str = '') -> ProxyServer:
        proxy = ProxyServer(host, port, protocol, country, username, password)
        self.proxies.append(proxy)
        self._save()
        return proxy
    
    def remove_proxy(self, host: str, port: int) -> bool:
        initial_len = len(self.proxies)
        self.proxies = [p for p in self.proxies 
                       if not (p.host == host and p.port == port)]
        if len(self.proxies) < initial_len:
            self._save()
            return True
        return False
    
    def get_working_proxies(self) -> List[ProxyServer]:
        return [p for p in self.proxies if p.working]
    
    def get_proxies_by_country(self, country: str) -> List[ProxyServer]:
        return [p for p in self.proxies if p.country == country]
    
    def check_all_proxies(self, threaded: bool = True):
        def check(proxy):
            proxy.check_latency()
        
        if threaded:
            threads = [threading.Thread(target=check, args=(p,)) for p in self.proxies]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        else:
            for p in self.proxies:
                p.check_latency()
        
        self._save()
    
    def select_best_proxy(self) -> Optional[ProxyServer]:
        working = self.get_working_proxies()
        if not working:
            return None
        
        return min(working, key=lambda p: p.latency)
    
    def select_random_proxy(self) -> Optional[ProxyServer]:
        working = self.get_working_proxies()
        if not working:
            return None
        return random.choice(working)
    
    def select_proxy_by_country(self, country: str) -> Optional[ProxyServer]:
        country_proxies = self.get_proxies_by_country(country)
        working = [p for p in country_proxies if p.working]
        if not working:
            return None
        return min(working, key=lambda p: p.latency)
    
    def connect(self, proxy: ProxyServer = None):
        if proxy:
            self.current_proxy = proxy
        else:
            self.current_proxy = self.select_best_proxy()
        
        if self.current_proxy:
            self.enabled = True
            self.last_rotation = datetime.now()
    
    def disconnect(self):
        self.current_proxy = None
        self.enabled = False
    
    def rotate(self):
        if self.rotation_mode == 'sequential':
            working = self.get_working_proxies()
            if not working:
                return
            
            if self.current_proxy:
                try:
                    idx = working.index(self.current_proxy)
                    next_idx = (idx + 1) % len(working)
                    self.current_proxy = working[next_idx]
                except:
                    self.current_proxy = working[0]
            else:
                self.current_proxy = working[0]
        
        elif self.rotation_mode == 'random':
            self.current_proxy = self.select_random_proxy()
        
        elif self.rotation_mode == 'best':
            self.current_proxy = self.select_best_proxy()
        
        self.last_rotation = datetime.now()
    
    def should_rotate(self) -> bool:
        if not self.auto_rotate or not self.enabled:
            return False
        
        if not self.last_rotation:
            return True
        
        elapsed = (datetime.now() - self.last_rotation).total_seconds()
        return elapsed >= self.rotate_interval
    
    def get_proxy_dict(self) -> Optional[Dict]:
        if not self.current_proxy:
            return None
        return {
            'host': self.current_proxy.host,
            'port': self.current_proxy.port,
            'protocol': self.current_proxy.protocol
        }
    
    def get_stats(self) -> Dict:
        total = len(self.proxies)
        working = len(self.get_working_proxies())
        
        countries = {}
        for p in self.proxies:
            if p.country:
                countries[p.country] = countries.get(p.country, 0) + 1
        
        return {
            'total_proxies': total,
            'working_proxies': working,
            'enabled': self.enabled,
            'current_proxy': self.current_proxy.to_dict() if self.current_proxy else None,
            'countries': countries,
            'auto_rotate': self.auto_rotate,
            'rotation_mode': self.rotation_mode
        }
    
    def set_rotation_mode(self, mode: str):
        if mode in ['sequential', 'random', 'best']:
            self.rotation_mode = mode
    
    def set_auto_rotate(self, enabled: bool, interval: int = 300):
        self.auto_rotate = enabled
        self.rotate_interval = interval
    
    def import_proxies(self, filepath: str):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        try:
                            port = int(parts[1])
                            self.add_proxy(parts[0], port)
                        except:
                            pass
    
    def export_proxies(self, filepath: str):
        with open(filepath, 'w') as f:
            for p in self.proxies:
                f.write(f"{p.host}:{p.port}\n")


class VPNProfile:
    def __init__(self, name: str, protocol: str = 'openvpn',
                 server: str = '', port: int = 1194,
                 username: str = '', password: str = ''):
        self.name = name
        self.protocol = protocol
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.config = ''
        self.enabled = False


class VPNManager:
    def __init__(self):
        self.profiles: List[VPNProfile] = []
        self.current_profile: Optional[VPNProfile] = None
        self.connected = False
        self.bytes_sent = 0
        self.bytes_received = 0
        self.connected_at = None
        self._load_default_profiles()
    
    def _load_default_profiles(self):
        pass
    
    def add_profile(self, name: str, protocol: str = 'openvpn',
                   server: str = '', port: int = 1194) -> VPNProfile:
        profile = VPNProfile(name, protocol, server, port)
        self.profiles.append(profile)
        return profile
    
    def remove_profile(self, name: str) -> bool:
        initial_len = len(self.profiles)
        self.profiles = [p for p in self.profiles if p.name != name]
        return len(self.profiles) < initial_len
    
    def connect(self, profile: VPNProfile):
        self.current_profile = profile
        self.connected = True
        self.connected_at = datetime.now()
        self.bytes_sent = 0
        self.bytes_received = 0
    
    def disconnect(self):
        self.current_profile = None
        self.connected = False
        self.connected_at = None
    
    def is_connected(self) -> bool:
        return self.connected
    
    def get_connection_time(self) -> Optional[timedelta]:
        if not self.connected or not self.connected_at:
            return None
        return datetime.now() - self.connected_at
    
    def get_stats(self) -> Dict:
        return {
            'connected': self.connected,
            'profile': self.current_profile.name if self.current_profile else None,
            'server': self.current_profile.server if self.current_profile else None,
            'protocol': self.current_profile.protocol if self.current_profile else None,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'connection_time': str(self.get_connection_time()) if self.get_connection_time() else None
        }
    
    def format_bytes(self, bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"
