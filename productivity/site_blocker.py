import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from enum import Enum

DATA_DIR = os.path.expanduser('~/.simple_browser')
BLOCKER_FILE = os.path.join(DATA_DIR, 'site_blocker.json')


class BlockRule:
    def __init__(self, pattern: str, rule_type: str = 'domain',
                 reason: str = '', enabled: bool = True):
        self.pattern = pattern
        self.rule_type = rule_type
        self.reason = reason
        self.enabled = enabled
        self.created_at = datetime.now().isoformat()
        self.hit_count = 0
        self.last_hit = None
        
        if rule_type == 'regex':
            try:
                self.compiled = re.compile(pattern, re.IGNORECASE)
            except:
                self.compiled = None
        else:
            self.compiled = None
    
    def matches(self, url: str) -> bool:
        if not self.enabled:
            return False
        
        url_lower = url.lower()
        
        if self.rule_type == 'domain':
            return self.pattern.lower() in url_lower
        
        elif self.rule_type == 'exact':
            return url_lower == self.pattern.lower()
        
        elif self.rule_type == 'prefix':
            return url_lower.startswith(self.pattern.lower())
        
        elif self.rule_type == 'regex' and self.compiled:
            return bool(self.compiled.search(url))
        
        return False
    
    def record_hit(self):
        self.hit_count += 1
        self.last_hit = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'pattern': self.pattern,
            'rule_type': self.rule_type,
            'reason': self.reason,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'hit_count': self.hit_count,
            'last_hit': self.last_hit
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BlockRule':
        rule = cls(
            data['pattern'], data.get('rule_type', 'domain'),
            data.get('reason', ''), data.get('enabled', True)
        )
        rule.created_at = data.get('created_at', rule.created_at)
        rule.hit_count = data.get('hit_count', 0)
        rule.last_hit = data.get('last_hit')
        return rule


class BlockCategory:
    def __init__(self, name: str, description: str = '', icon: str = '🚫'):
        self.name = name
        self.description = description
        self.icon = icon
        self.rules: List[BlockRule] = []
        self.enabled = True
    
    def add_rule(self, rule: BlockRule):
        self.rules.append(rule)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'enabled': self.enabled,
            'rules': [r.to_dict() for r in self.rules]
        }


class SiteBlocker:
    def __init__(self):
        self.enabled = False
        self.rules: List[BlockRule] = []
        self.whitelist: List[str] = []
        self.categories: List[BlockCategory] = []
        self.blocked_count = 0
        self.schedule_enabled = False
        self.schedule_start = '09:00'
        self.schedule_end = '17:00'
        self.schedule_days = [0, 1, 2, 3, 4]
        
        self.blocked_pages: List[Dict] = []
        
        self.on_block_callbacks: List[Callable] = []
        
        self._load_default_categories()
        self._load()
    
    def _load_default_categories(self):
        social = BlockCategory('social', 'Social media', '📱')
        social.add_rule(BlockRule('facebook.com', 'domain', 'Social media'))
        social.add_rule(BlockRule('twitter.com', 'domain', 'Social media'))
        social.add_rule(BlockRule('instagram.com', 'domain', 'Social media'))
        social.add_rule(BlockRule('tiktok.com', 'domain', 'Social media'))
        social.add_rule(BlockRule('reddit.com', 'domain', 'Social media'))
        social.add_rule(BlockRule('vk.com', 'domain', 'Social media'))
        self.categories.append(social)
        
        entertainment = BlockCategory('entertainment', 'Entertainment', '🎬')
        entertainment.add_rule(BlockRule('youtube.com', 'domain', 'Entertainment'))
        entertainment.add_rule(BlockRule('netflix.com', 'domain', 'Entertainment'))
        entertainment.add_rule(BlockRule('twitch.tv', 'domain', 'Entertainment'))
        entertainment.add_rule(BlockRule('spotify.com', 'domain', 'Entertainment'))
        self.categories.append(entertainment)
        
        news = BlockCategory('news', 'News sites', '📰')
        news.add_rule(BlockRule('news.ycombinator.com', 'domain', 'News'))
        self.categories.append(news)
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(BLOCKER_FILE):
            try:
                with open(BLOCKER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.enabled = data.get('enabled', False)
                    self.rules = [BlockRule.from_dict(r) for r in data.get('rules', [])]
                    self.whitelist = data.get('whitelist', [])
                    self.blocked_count = data.get('blocked_count', 0)
                    self.schedule_enabled = data.get('schedule_enabled', False)
                    self.schedule_start = data.get('schedule_start', '09:00')
                    self.schedule_end = data.get('schedule_end', '17:00')
                    self.schedule_days = data.get('schedule_days', [0, 1, 2, 3, 4])
            except:
                pass
    
    def _save(self):
        data = {
            'enabled': self.enabled,
            'rules': [r.to_dict() for r in self.rules],
            'whitelist': self.whitelist,
            'blocked_count': self.blocked_count,
            'schedule_enabled': self.schedule_enabled,
            'schedule_start': self.schedule_start,
            'schedule_end': self.schedule_end,
            'schedule_days': self.schedule_days
        }
        with open(BLOCKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def should_block(self, url: str) -> tuple[bool, Optional[BlockRule]]:
        if not self.enabled:
            return False, None
        
        if self.is_whitelisted(url):
            return False, None
        
        if self.schedule_enabled and not self.is_schedule_active():
            return False, None
        
        for rule in self.rules:
            if rule.matches(url):
                rule.record_hit()
                self.blocked_count += 1
                
                self.blocked_pages.append({
                    'url': url,
                    'rule': rule.pattern,
                    'timestamp': datetime.now().isoformat()
                })
                
                self._notify_block(url, rule)
                self._save()
                return True, rule
        
        return False, None
    
    def is_whitelisted(self, url: str) -> bool:
        url_lower = url.lower()
        for item in self.whitelist:
            if item.lower() in url_lower:
                return True
        return False
    
    def is_schedule_active(self) -> bool:
        now = datetime.now()
        current_day = now.weekday()
        
        if current_day not in self.schedule_days:
            return False
        
        current_time = now.time()
        start_time = datetime.strptime(self.schedule_start, '%H:%M').time()
        end_time = datetime.strptime(self.schedule_end, '%H:%M').time()
        
        return start_time <= current_time <= end_time
    
    def add_rule(self, pattern: str, rule_type: str = 'domain', reason: str = ''):
        rule = BlockRule(pattern, rule_type, reason)
        self.rules.append(rule)
        self._save()
    
    def remove_rule(self, pattern: str) -> bool:
        initial_len = len(self.rules)
        self.rules = [r for r in self.rules if r.pattern != pattern]
        if len(self.rules) < initial_len:
            self._save()
            return True
        return False
    
    def enable_rule(self, pattern: str) -> bool:
        for rule in self.rules:
            if rule.pattern == pattern:
                rule.enabled = True
                self._save()
                return True
        return False
    
    def disable_rule(self, pattern: str) -> bool:
        for rule in self.rules:
            if rule.pattern == pattern:
                rule.enabled = False
                self._save()
                return True
        return False
    
    def add_to_whitelist(self, domain: str):
        if domain not in self.whitelist:
            self.whitelist.append(domain)
            self._save()
    
    def remove_from_whitelist(self, domain: str) -> bool:
        if domain in self.whitelist:
            self.whitelist.remove(domain)
            self._save()
            return True
        return False
    
    def toggle(self):
        self.enabled = not self.enabled
        self._save()
    
    def get_blocked_domains(self) -> List[str]:
        return [r.pattern for r in self.rules if r.enabled]
    
    def get_blocked_pages(self, limit: int = 50) -> List[Dict]:
        return self.blocked_pages[-limit:]
    
    def get_stats(self) -> Dict:
        category_stats = {}
        for cat in self.categories:
            count = sum(1 for r in cat.rules if r.enabled)
            category_stats[cat.name] = count
        
        return {
            'enabled': self.enabled,
            'total_rules': len(self.rules),
            'enabled_rules': sum(1 for r in self.rules if r.enabled),
            'whitelist_count': len(self.whitelist),
            'blocked_count': self.blocked_count,
            'schedule_enabled': self.schedule_enabled,
            'is_schedule_active': self.is_schedule_active() if self.schedule_enabled else None,
            'categories': category_stats
        }
    
    def set_schedule(self, enabled: bool, start: str = '09:00', 
                    end: str = '17:00', days: List[int] = None):
        self.schedule_enabled = enabled
        self.schedule_start = start
        self.schedule_end = end
        if days:
            self.schedule_days = days
        self._save()
    
    def get_most_blocked(self, limit: int = 10) -> List[Dict]:
        rule_counts = {}
        for rule in self.rules:
            if rule.hit_count > 0:
                rule_counts[rule.pattern] = rule.hit_count
        
        sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'pattern': p, 'count': c} for p, c in sorted_rules[:limit]]
    
    def on_block(self, callback: Callable):
        self.on_block_callbacks.append(callback)
    
    def _notify_block(self, url: str, rule: BlockRule):
        for callback in self.on_block_callbacks:
            try:
                callback(url, rule)
            except:
                pass
    
    def export_rules(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            for rule in self.rules:
                f.write(f"{rule.pattern}\n")
    
    def import_rules(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                pattern = line.strip()
                if pattern and not pattern.startswith('#'):
                    self.add_rule(pattern)


class ProductivityScore:
    def __init__(self):
        self.focus_points = 0
        self.distraction_points = 0
        self.daily_scores: Dict[str, int] = {}
    
    def add_focus(self, points: int = 10):
        self.focus_points += points
        today = datetime.now().date().isoformat()
        self.daily_scores[today] = self.daily_scores.get(today, 0) + points
    
    def add_distraction(self, points: int = 5):
        self.distraction_points += points
    
    def get_score(self) -> int:
        return max(0, self.focus_points - self.distraction_points)
    
    def get_daily_score(self, date: str = None) -> int:
        if date is None:
            date = datetime.now().date().isoformat()
        return self.daily_scores.get(date, 0)
    
    def get_weekly_average(self) -> float:
        total = 0
        count = 0
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            if date in self.daily_scores:
                total += self.daily_scores[date]
                count += 1
        return total / count if count > 0 else 0
