import re
from typing import List, Dict, Set, Optional
from collections import defaultdict


class TrackerPattern:
    def __init__(self, pattern: str, category: str, description: str = ''):
        self.pattern = pattern
        self.compiled = re.compile(pattern, re.IGNORECASE)
        self.category = category
        self.description = description


class Tracker:
    def __init__(self, domain: str, category: str, blocked_count: int = 0):
        self.domain = domain
        self.category = category
        self.blocked_count = blocked_count
        self.first_seen = None
        self.last_seen = None


class TrackerBlocker:
    def __init__(self):
        self.enabled = True
        self.blocked_domains: Set[str] = set()
        self.whitelist: Set[str] = set()
        self.trackers: Dict[str, Tracker] = {}
        self.stats = {
            'total_blocked': 0,
            'by_category': defaultdict(int),
            'by_domain': defaultdict(int)
        }
        self._load_default_filters()
    
    def _load_default_filters(self):
        self.filters: List[TrackerPattern] = [
            TrackerPattern(r'.*\.google-analytics\.com', 'analytics', 'Google Analytics'),
            TrackerPattern(r'.*\.googletagmanager\.com', 'analytics', 'Google Tag Manager'),
            TrackerPattern(r'.*\.facebook\.net/.*signals', 'social', 'Facebook Pixel'),
            TrackerPattern(r'.*\.facebook\.com/tr', 'social', 'Facebook Tracking'),
            TrackerPattern(r'.*\.hotjar\.com', 'analytics', 'Hotjar'),
            TrackerPattern(r'.*\.mixpanel\.com', 'analytics', 'Mixpanel'),
            TrackerPattern(r'.*\.segment\.io', 'analytics', 'Segment'),
            TrackerPattern(r'.*\.segment.com', 'analytics', 'Segment'),
            TrackerPattern(r'.*\.amplitude\.com', 'analytics', 'Amplitude'),
            TrackerPattern(r'.*\.newrelic\.com', 'analytics', 'New Relic'),
            TrackerPattern(r'.*\.fullstory\.com', 'analytics', 'FullStory'),
            TrackerPattern(r'.*\.mouseflow\.com', 'analytics', 'Mouseflow'),
            TrackerPattern(r'.*\.crazyegg\.com', 'analytics', 'Crazy Egg'),
            TrackerPattern(r'.*\.luckyorange\.com', 'analytics', 'Lucky Orange'),
            TrackerPattern(r'.*\.quantserve\.com', 'analytics', 'Quantcast'),
            TrackerPattern(r'.*\.scorecardresearch\.com', 'analytics', 'Comscore'),
            TrackerPattern(r'.*\.doubleclick\.net', 'advertising', 'DoubleClick'),
            TrackerPattern(r'.*\.googlesyndication\.com', 'advertising', 'Google Ads'),
            TrackerPattern(r'.*\.adnxs\.com', 'advertising', 'AppNexus'),
            TrackerPattern(r'.*\.adsrvr\.org', 'advertising', 'The Trade Desk'),
            TrackerPattern(r'.*\.advertising\.com', 'advertising', 'Advertising.com'),
            TrackerPattern(r'.*\.criteo\.com', 'advertising', 'Criteo'),
            TrackerPattern(r'.*\.taboola\.com', 'advertising', 'Taboola'),
            TrackerPattern(r'.*\.outbrain\.com', 'advertising', 'Outbrain'),
            TrackerPattern(r'.*\.amazon-adsystem\.com', 'advertising', 'Amazon Ads'),
            TrackerPattern(r'.*\.bing\.com/bat\.js', 'advertizing', 'Bing Ads'),
            TrackerPattern(r'.*\.twitter\.com/.*collect', 'social', 'Twitter Analytics'),
            TrackerPattern(r'.*\.linkedin\.com/px', 'social', 'LinkedIn Pixel'),
            TrackerPattern(r'.*\.tiktok\.com/.*event', 'social', 'TikTok Pixel'),
            TrackerPattern(r'.*coinhive\..*', 'cryptomining', 'CoinHive'),
            TrackerPattern(r'.*coin-hive\..*', 'cryptomining', 'CoinHive'),
            TrackerPattern(r'.*cryptoloot\..*', 'cryptomining', 'CryptoLoot'),
            TrackerPattern(r'.*minero\.cc', 'cryptomining', 'Minero'),
            TrackerPattern(r'.*webminer\..*', 'cryptomining', 'Web Miner'),
            TrackerPattern(r'.*jsecoin\..*', 'cryptomining', 'JSEcoin'),
            TrackerPattern(r'.*\.branch\.io', 'fingerprinting', 'Branch'),
            TrackerPattern(r'.*\.fingerprintjs\.com', 'fingerprinting', 'FingerprintJS'),
            TrackerPattern(r'.*\.iovation\.com', 'fingerprinting', 'IOvation'),
            TrackerPattern(r'.*\.maxmind\.com', 'fingerprinting', 'MaxMind'),
            TrackerPattern(r'.*\.optimizely\.com', 'ab_testing', 'Optimizely'),
            TrackerPattern(r'.*\.vwo\.com', 'ab_testing', 'VWO'),
            TrackerPattern(r'.*\.omniture\.com', 'analytics', 'Adobe Analytics'),
            TrackerPattern(r'.*\.omtrdc\.net', 'analytics', 'Adobe Analytics'),
            TrackerPattern(r'.*\.mookie1\.com', 'advertising', 'Mookie1'),
            TrackerPattern(r'.*\.2mdn\.net', 'advertising', 'DoubleClick Manager'),
            TrackerPattern(r'.*\.adform\.net', 'advertising', 'Adform'),
            TrackerPattern(r'.*\.smartadserver\.com', 'advertising', 'Smart AdServer'),
            TrackerPattern(r'.*\.rubiconproject\.com', 'advertising', 'Rubicon'),
            TrackerPattern(r'.*\.pubmatic\.com', 'advertising', 'PubMatic'),
            TrackerPattern(r'.*\.openx\.net', 'advertising', 'OpenX'),
            TrackerTrackerPattern(r'.*\.bidswitch\.net', 'advertising', 'BidSwitch'),
            TrackerPattern(r'.*\.casalemedia\.com', 'advertising', 'Casale Media'),
            TrackerPattern(r'.*\.indexexchange\.com', 'advertising', 'Index Exchange'),
            TrackerPattern(r'.*\.sharethrough\.com', 'advertising', 'ShareThrough'),
            TrackerPattern(r'.*\.spotxchange\.com', 'advertising', 'SpotXchange'),
            TrackerPattern(r'.*\.yieldmo\.com', 'advertising', 'YieldMo'),
            TrackerPattern(r'.*\.contextweb\.com', 'advertising', 'ContextWeb'),
            TrackerPattern(r'.*\.media\.net', 'advertising', 'Media.net'),
        ]
        
        common_trackers = [
            'google-analytics.com', 'googletagmanager.com', 'facebook.net',
            'hotjar.com', 'mixpanel.com', 'segment.io', 'amplitude.com',
            'doubleclick.net', 'googlesyndication.com', 'adnxs.com',
            'criteo.com', 'taboola.com', 'outbrain.com', 'amazon-adsystem.com'
        ]
        self.blocked_domains.update(common_trackers)
    
    def should_block(self, url: str, page_domain: str = '') -> tuple[bool, Optional[TrackerPattern]]:
        if not self.enabled:
            return False, None
        
        domain = self._extract_domain(url)
        
        if domain in self.whitelist:
            return False, None
        
        if domain in self.blocked_domains:
            self._record_block(domain, 'manual')
            return True, None
        
        for tracker_filter in self.filters:
            if tracker_filter.compiled.match(url):
                self._record_block(domain, tracker_filter.category)
                return True, tracker_filter
        
        return False, None
    
    def _extract_domain(self, url: str) -> str:
        if '://' in url:
            domain = url.split('/')[2]
        else:
            domain = url.split('/')[0]
        return domain.split(':')[0]
    
    def _record_block(self, domain: str, category: str):
        self.stats['total_blocked'] += 1
        self.stats['by_category'][category] += 1
        self.stats['by_domain'][domain] += 1
        
        if domain not in self.trackers:
            self.trackers[domain] = Tracker(domain, category)
        self.trackers[domain].blocked_count += 1
    
    def add_filter(self, pattern: str, category: str = 'custom', description: str = ''):
        try:
            tracker_filter = TrackerPattern(pattern, category, description)
            self.filters.append(tracker_filter)
        except:
            pass
    
    def remove_filter(self, pattern: str):
        self.filters = [f for f in self.filters if f.pattern != pattern]
    
    def block_domain(self, domain: str):
        self.blocked_domains.add(domain)
    
    def unblock_domain(self, domain: str):
        self.blocked_domains.discard(domain)
    
    def whitelist_domain(self, domain: str):
        self.whitelist.add(domain)
    
    def remove_whitelist(self, domain: str):
        self.whitelist.discard(domain)
    
    def get_blocked_domains(self) -> List[str]:
        return list(self.blocked_domains)
    
    def get_whitelist(self) -> List[str]:
        return list(self.whitelist)
    
    def get_stats(self) -> Dict:
        return {
            'total_blocked': self.stats['total_blocked'],
            'by_category': dict(self.stats['by_category']),
            'top_trackers': sorted(
                [(d, t.blocked_count) for d, t in self.trackers.items()],
                key=lambda x: x[1], reverse=True
            )[:20]
        }
    
    def get_category_stats(self) -> Dict[str, int]:
        return dict(self.stats['by_category'])
    
    def clear_stats(self):
        self.stats = {
            'total_blocked': 0,
            'by_category': defaultdict(int),
            'by_domain': defaultdict(int)
        }
        self.trackers.clear()
    
    def toggle(self):
        self.enabled = not self.enabled
    
    def load_filter_list(self, url: str):
        try:
            import requests
            response = requests.get(url, timeout=10)
            lines = response.text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('!'):
                    if line.startswith('||'):
                        domain = line[2:].strip('/')
                        self.block_domain(domain)
        except:
            pass
    
    def export_filters(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('! Tracker Blocker Filters\n')
            f.write(f'! Generated: {__import__("datetime").datetime.now()}\n\n')
            for domain in self.blocked_domains:
                f.write(f'||{domain}^\n')
    
    def import_filters(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('!'):
                    if line.startswith('||'):
                        domain = line[2:].strip('/^')
                        self.block_domain(domain)


class CryptoMinerBlocker(TrackerBlocker):
    def __init__(self):
        super().__init__()
        self._load_cryptominer_filters()
    
    def _load_cryptominer_filters(self):
        self.filters = [
            r'.*coinhive\..*',
            r'.*coin-hive\..*',
            r'.*cryptoloot\..*',
            r'.*minero\.cc',
            r'.*webminer\..*',
            r'.*jsecoin\..*',
            r'.*ppoi\..*',
            r'.*coinerra\..*',
            r'.*afminer\..*',
            r'.*coinimp\..*',
            r'.*webmine.pro',
            r'.*miner.pr0gramm.com',
            r'.*minecrunch.io',
            r'.*minero.xyz',
            r'.*webmine.io',
            r'.*freemining.co',
            r'.*free-mining.io',
            r'.*hashcoins.me',
            r'.*coinblind.com',
            r'.*miner.bitcoin.cz',
            r'.*cryptomining.game',
            r'.*coin-hive.com',
            r'.*patoshi.io',
        ]
        
        self.compiled = [re.compile(f, re.IGNORECASE) for f in self.filters]
        
        self.domains = [
            'coinhive.com', 'coin-hive.com', 'cryptoloot.pro',
            'minero.cc', 'webminer.net', 'jsecoin.com'
        ]
        self.blocked_domains.update(self.domains)
    
    def should_block(self, url: str) -> bool:
        if not self.enabled:
            return False
        
        for pattern in self.compiled:
            if pattern.search(url):
                return True
        
        domain = self._extract_domain(url)
        return domain in self.blocked_domains


class FingerprintProtector:
    def __init__(self):
        self.enabled = False
        self.canvas_protection = True
        self.audio_protection = True
        self.webgl_protection = True
        self.font_protection = True
        self.screen_protection = True
    
    def get_canvas_fingerprint(self, data: str) -> str:
        if self.enabled and self.canvas_protection:
            import hashlib
            return hashlib.sha256(data + 'noise').hexdigest()
        return data
    
    def get_webgl_fingerprint(self, renderer: str) -> str:
        if self.enabled and self.webgl_protection:
            return 'Generic WebGL Renderer'
        return renderer
    
    def get_audio_fingerprint(self) -> dict:
        if self.enabled and self.audio_protection:
            return {'fingerprint': 'blocked'}
        return {}
    
    def get_screen_info(self, width: int, height: int) -> dict:
        if self.enabled and self.screen_protection:
            return {
                'width': 1920,
                'height': 1080,
                'colorDepth': 24,
                'pixelRatio': 1
            }
        return {'width': width, 'height': height}
    
    def get_fonts(self) -> list:
        if self.enabled and self.font_protection:
            return ['Arial', 'Times New Roman', 'Courier New']
        return []
    
    def generate_noise(self) -> str:
        import random
        import string
        return ''.join(random.choices(string.ascii_letters, k=32))
