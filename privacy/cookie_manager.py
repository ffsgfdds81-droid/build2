import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

DATA_DIR = os.path.expanduser('~/.simple_browser')
COOKIES_FILE = os.path.join(DATA_DIR, 'cookies.json')


class Cookie:
    def __init__(self, name: str, value: str, domain: str, path: str = '/',
                 expires: str = None, http_only: bool = False, secure: bool = False,
                 same_site: str = 'none', created_at: str = None):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.expires = expires
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.created_at = created_at or datetime.now().isoformat()
        self.last_accessed = created_at
    
    def is_expired(self) -> bool:
        if not self.expires:
            return False
        try:
            expire_date = datetime.fromisoformat(self.expires)
            return expire_date < datetime.now()
        except:
            return False
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'value': self.value,
            'domain': self.domain,
            'path': self.path,
            'expires': self.expires,
            'http_only': self.http_only,
            'secure': self.secure,
            'same_site': self.same_site,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Cookie':
        cookie = cls(
            data['name'], data['value'], data['domain'],
            data.get('path', '/'), data.get('expires'),
            data.get('http_only', False), data.get('secure', False),
            data.get('same_site', 'none'), data.get('created_at')
        )
        cookie.last_accessed = data.get('last_accessed', cookie.last_accessed)
        return cookie


class CookieManager:
    def __init__(self):
        self.cookies: Dict[str, Dict[str, Cookie]] = defaultdict(dict)
        self.blocked_domains: set = set()
        self.allowed_domains: set = set()
        self.auto_delete_enabled = False
        self.auto_delete_days = 30
        self.third_party_blocking = False
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for domain, cookies in data.get('cookies', {}).items():
                        self.cookies[domain] = {
                            name: Cookie.from_dict(c) 
                            for name, c in cookies.items()
                        }
                    self.blocked_domains = set(data.get('blocked_domains', []))
                    self.allowed_domains = set(data.get('allowed_domains', []))
            except:
                pass
    
    def _save(self):
        data = {
            'cookies': {
                domain: {name: c.to_dict() for name, c in cookies.items()}
                for domain, cookies in self.cookies.items()
            },
            'blocked_domains': list(self.blocked_domains),
            'allowed_domains': list(self.allowed_domains)
        }
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_cookie(self, domain: str, name: str, value: str, **kwargs) -> Cookie:
        if self.is_domain_blocked(domain):
            return None
        
        cookie = Cookie(name, value, domain, **kwargs)
        
        if self.blocked_domains or self.allowed_domains:
            if self.allowed_domains and domain not in self.allowed_domains:
                return None
        
        self.cookies[domain][name] = cookie
        self._save()
        return cookie
    
    def get_cookie(self, domain: str, name: str) -> Optional[Cookie]:
        if domain in self.cookies:
            cookie = self.cookies[domain].get(name)
            if cookie and not cookie.is_expired():
                cookie.last_accessed = datetime.now().isoformat()
                return cookie
        return None
    
    def get_all_cookies(self, domain: str = None) -> List[Cookie]:
        if domain:
            return list(self.cookies.get(domain, {}).values())
        
        all_cookies = []
        for cookies in self.cookies.values():
            all_cookies.extend(c for c in cookies.values() if not c.is_expired())
        return all_cookies
    
    def get_cookies_dict(self, domain: str) -> Dict[str, str]:
        result = {}
        for name, cookie in self.cookies.get(domain, {}).items():
            if not cookie.is_expired():
                result[name] = cookie.value
        return result
    
    def delete_cookie(self, domain: str, name: str) -> bool:
        if domain in self.cookies and name in self.cookies[domain]:
            del self.cookies[domain][name]
            self._save()
            return True
        return False
    
    def delete_all_cookies(self, domain: str = None):
        if domain:
            if domain in self.cookies:
                self.cookies[domain] = {}
        else:
            self.cookies.clear()
        self._save()
    
    def delete_expired(self):
        for domain in list(self.cookies.keys()):
            expired = [
                name for name, cookie in self.cookies[domain].items()
                if cookie.is_expired()
            ]
            for name in expired:
                del self.cookies[domain][name]
            
            if not self.cookies[domain]:
                del self.cookies[domain]
        self._save()
    
    def delete_older_than(self, days: int):
        cutoff = datetime.now() - timedelta(days=days)
        for domain in list(self.cookies.keys()):
            for name, cookie in list(self.cookies[domain].items()):
                accessed = datetime.fromisoformat(cookie.last_accessed)
                if accessed < cutoff:
                    del self.cookies[domain][name]
            
            if not self.cookies[domain]:
                del self.cookies[domain]
        self._save()
    
    def block_domain(self, domain: str):
        self.blocked_domains.add(domain)
        self._save()
    
    def unblock_domain(self, domain: str):
        self.blocked_domains.discard(domain)
        self._save()
    
    def allow_domain(self, domain: str):
        self.allowed_domains.add(domain)
        self._save()
    
    def disallow_domain(self, domain: str):
        self.allowed_domains.discard(domain)
        self._save()
    
    def is_domain_blocked(self, domain: str) -> bool:
        return domain in self.blocked_domains
    
    def get_blocked_domains(self) -> List[str]:
        return list(self.blocked_domains)
    
    def get_stats(self) -> Dict:
        total = sum(len(c) for c in self.cookies.values())
        domains = len(self.cookies)
        
        cookie_counts = defaultdict(int)
        for cookies in self.cookies.values():
            for cookie in cookies.values():
                cookie_counts[cookie.domain] += 1
        
        top_domains = sorted(cookie_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_cookies': total,
            'domains': domains,
            'blocked_domains': len(self.blocked_domains),
            'allowed_domains': len(self.allowed_domains),
            'top_domains': dict(top_domains)
        }
    
    def export_cookiejar(self, filepath: str):
        import http.cookiejar
        jar = http.cookiejar.LWPCookieJar()
        
        for domain, cookies in self.cookies.items():
            for cookie in cookies.values():
                if not cookie.is_expired():
                    c = http.cookiejar.Cookie(
                        version=0,
                        name=cookie.name,
                        value=cookie.value,
                        port=None,
                        port_specified=False,
                        domain=cookie.domain,
                        domain_specified=True,
                        domain_initial_dot=False,
                        path=cookie.path,
                        path_specified=True,
                        secure=cookie.secure,
                        expires=None,
                        discard=True,
                        comment=None,
                        comment_url=None,
                        rest={},
                        rfc2109=False
                    )
                    jar.set_cookie(c)
        
        jar.save(filepath, ignore_discard=True)
    
    def import_cookiejar(self, filepath: str):
        import http.cookiejar
        try:
            jar = http.cookiejar.LWPCookieJar()
            jar.load(filepath, ignore_discard=True)
            
            for cookie in jar:
                self.set_cookie(
                    cookie.domain, cookie.name, cookie.value,
                    path=cookie.path, secure=cookie.secure
                )
        except:
            pass
    
    def enable_auto_delete(self, days: int = 30):
        self.auto_delete_enabled = True
        self.auto_delete_days = days
        self.delete_older_than(days)
    
    def disable_auto_delete(self):
        self.auto_delete_enabled = False
    
    def set_third_party_blocking(self, enabled: bool):
        self.third_party_blocking = enabled
    
    def should_block_third_party(self, cookie_domain: str, page_domain: str) -> bool:
        if not self.third_party_blocking:
            return False
        return cookie_domain != page_domain and not cookie_domain.endswith(page_domain)
