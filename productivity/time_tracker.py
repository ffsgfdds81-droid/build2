import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

DATA_DIR = os.path.expanduser('~/.simple_browser')
TRACKER_FILE = os.path.join(DATA_DIR, 'time_tracker.json')


class SiteVisit:
    def __init__(self, url: str, title: str = '', duration: int = 0):
        self.url = url
        self.title = title
        self.domain = self._extract_domain(url)
        self.duration = duration
        self.start_time = datetime.now()
        self.end_time = None
        self.date = datetime.now().date().isoformat()
    
    def _extract_domain(self, url: str) -> str:
        if '://' in url:
            domain = url.split('/')[2]
        else:
            domain = url.split('/')[0]
        return domain.split(':')[0]
    
    def end_visit(self):
        self.end_time = datetime.now()
        self.duration = int((self.end_time - self.start_time).total_seconds())
    
    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'domain': self.domain,
            'duration': self.duration,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'date': self.date
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SiteVisit':
        visit = cls(data['url'], data.get('title', ''), data.get('duration', 0))
        visit.domain = data.get('domain', visit.domain)
        visit.start_time = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            visit.end_time = datetime.fromisoformat(data['end_time'])
        visit.date = data.get('date', visit.date)
        return visit


class TimeTracker:
    def __init__(self):
        self.current_visit: Optional[SiteVisit] = None
        self.visits: List[SiteVisit] = []
        self.daily_limits: Dict[str, int] = {}
        self.daily_warnings: Dict[str, List[str]] = defaultdict(list)
        self.enabled = True
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(TRACKER_FILE):
            try:
                with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.visits = [SiteVisit.from_dict(v) for v in data.get('visits', [])]
                    self.daily_limits = data.get('daily_limits', {})
            except:
                pass
    
    def _save(self):
        data = {
            'visits': [v.to_dict() for v in self.visits],
            'daily_limits': self.daily_limits
        }
        with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def start_tracking(self, url: str, title: str = ''):
        if not self.enabled:
            return
        
        if self.current_visit:
            self.stop_tracking()
        
        self.current_visit = SiteVisit(url, title)
    
    def stop_tracking(self) -> Optional[SiteVisit]:
        if not self.current_visit:
            return None
        
        self.current_visit.end_visit()
        
        if self.current_visit.duration > 0:
            self.visits.append(self.current_visit)
            self._check_daily_limit(self.current_visit.domain, self.current_visit.duration)
            self._save()
        
        self.current_visit = None
        return self.current_visit
    
    def update_title(self, title: str):
        if self.current_visit:
            self.current_visit.title = title
    
    def _check_daily_limit(self, domain: str, duration: int):
        limit = self.daily_limits.get(domain)
        if not limit:
            return
        
        today = datetime.now().date().isoformat()
        total_today = self.get_domain_time_today(domain)
        
        if total_today >= limit and domain not in self.daily_warnings[today]:
            self.daily_warnings[today].append(domain)
    
    def get_domain_time_today(self, domain: str) -> int:
        today = datetime.now().date().isoformat()
        total = 0
        for visit in self.visits:
            if visit.domain == domain and visit.date == today:
                total += visit.duration
        if self.current_visit and self.current_visit.domain == domain:
            total += self.current_visit.duration
        return total
    
    def get_domain_time(self, domain: str, days: int = 7) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        total = 0
        for visit in self.visits:
            if visit.domain == domain and visit.date >= cutoff:
                total += visit.duration
        return total
    
    def get_daily_stats(self, date: str = None) -> Dict[str, int]:
        if date is None:
            date = datetime.now().date().isoformat()
        
        stats = defaultdict(int)
        for visit in self.visits:
            if visit.date == date:
                stats[visit.domain] += visit.duration
        
        return dict(stats)
    
    def get_weekly_stats(self) -> Dict[str, int]:
        stats = defaultdict(int)
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        
        for visit in self.visits:
            if visit.date >= week_ago:
                stats[visit.domain] += visit.duration
        
        return dict(stats)
    
    def get_top_sites(self, limit: int = 10, days: int = 7) -> List[Dict]:
        stats = defaultdict(int)
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        for visit in self.visits:
            if visit.date >= cutoff:
                stats[visit.domain] += visit.duration
        
        sorted_sites = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        return [
            {'domain': domain, 'duration': duration, 'formatted': self.format_duration(duration)}
            for domain, duration in sorted_sites[:limit]
        ]
    
    def get_category_stats(self) -> Dict[str, int]:
        categories = {
            'social': ['facebook.com', 'twitter.com', 'instagram.com', 'vk.com', 'tiktok.com'],
            'video': ['youtube.com', 'netflix.com', 'twitch.tv'],
            'news': ['reddit.com', 'news.ycombinator.com'],
            'work': ['github.com', 'stackoverflow.com', 'docs.google.com'],
        }
        
        stats = defaultdict(int)
        for category, domains in categories.items():
            for domain in domains:
                stats[category] += self.get_domain_time(domain)
        
        return dict(stats)
    
    def format_duration(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def set_daily_limit(self, domain: str, minutes: int):
        self.daily_limits[domain] = minutes * 60
        self._save()
    
    def remove_daily_limit(self, domain: str):
        if domain in self.daily_limits:
            del self.daily_limits[domain]
            self._save()
    
    def get_daily_limits(self) -> Dict[str, int]:
        return {k: v // 60 for k, v in self.daily_limits.items()}
    
    def get_total_time_today(self) -> int:
        today = datetime.now().date().isoformat()
        total = 0
        for visit in self.visits:
            if visit.date == today:
                total += visit.duration
        if self.current_visit:
            total += self.current_visit.duration
        return total
    
    def get_total_time_week(self) -> int:
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        total = 0
        for visit in self.visits:
            if visit.date >= week_ago:
                total += visit.duration
        return total
    
    def get_productivity_score(self) -> float:
        productive_domains = ['github.com', 'stackoverflow.com', 'docs.google.com', 
                             'drive.google.com', 'notion.so', 'trello.com']
        unproductive_domains = ['facebook.com', 'twitter.com', 'instagram.com',
                              'youtube.com', 'tiktok.com', 'reddit.com']
        
        productive_time = 0
        unproductive_time = 0
        
        for visit in self.visits:
            if visit.domain in productive_domains:
                productive_time += visit.duration
            elif visit.domain in unproductive_domains:
                unproductive_time += visit.duration
        
        total = productive_time + unproductive_time
        if total == 0:
            return 50.0
        
        score = (productive_time / total) * 100
        return round(score, 1)
    
    def get_hourly_distribution(self, days: int = 7) -> Dict[int, int]:
        distribution = defaultdict(int)
        cutoff = datetime.now() - timedelta(days=days)
        
        for visit in self.visits:
            if visit.start_time >= cutoff:
                hour = visit.start_time.hour
                distribution[hour] += visit.duration
        
        return dict(distribution)
    
    def clear_old_data(self, days: int = 30):
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        self.visits = [v for v in self.visits if v.date >= cutoff]
        self._save()
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'domain', 'url', 'title', 'duration_minutes'])
            for visit in self.visits:
                writer.writerow([
                    visit.date, visit.domain, visit.url, visit.title,
                    visit.duration // 60
                ])


class SessionAnalyzer:
    def __init__(self, tracker: TimeTracker):
        self.tracker = tracker
    
    def get_focus_sessions(self, min_duration: int = 300) -> List[Dict]:
        sessions = []
        current_session = []
        current_domain = None
        
        sorted_visits = sorted(self.tracker.visits, key=lambda v: v.start_time)
        
        for visit in sorted_visits:
            if current_domain is None:
                current_domain = visit.domain
                current_session.append(visit)
            elif visit.domain == current_domain:
                current_session.append(visit)
            else:
                if current_session:
                    total_duration = sum(v.duration for v in current_session)
                    if total_duration >= min_duration:
                        sessions.append({
                            'domain': current_domain,
                            'duration': total_duration,
                            'start': current_session[0].start_time.isoformat(),
                            'end': current_session[-1].end_time.isoformat() if current_session[-1].end_time else None
                        })
                current_domain = visit.domain
                current_session = [visit]
        
        return sessions
    
    def get_most_productive_day(self) -> str:
        daily_scores = {}
        
        for visit in self.tracker.visits:
            productive_domains = ['github.com', 'stackoverflow.com', 'docs.google.com']
            if visit.domain in productive_domains:
                daily_scores[visit.date] = daily_scores.get(visit.date, 0) + visit.duration
        
        if not daily_scores:
            return 'N/A'
        
        return max(daily_scores.items(), key=lambda x: x[1])[0]
    
    def get_time_waste_analysis(self) -> Dict:
        unproductive_domains = {
            'facebook.com': 'Social Media',
            'twitter.com': 'Social Media',
            'instagram.com': 'Social Media',
            'youtube.com': 'Video',
            'tiktok.com': 'Social Media',
            'reddit.com': 'News/Forums'
        }
        
        waste_by_category = defaultdict(int)
        
        for visit in self.tracker.visits:
            category = unproductive_domains.get(visit.domain, 'Other')
            waste_by_category[category] += visit.duration
        
        return dict(waste_by_category)
