import json
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
from html.parser import HTMLParser
import urllib.request
import urllib.parse

DATA_DIR = os.path.expanduser('~/.simple_browser')
RSS_FILE = os.path.join(DATA_DIR, 'rss_feeds.json')


class RSSItem:
    def __init__(self, title: str, link: str, description: str = '',
                 pub_date: str = '', author: str = '', guid: str = ''):
        self.title = title
        self.link = link
        self.description = description
        self.pub_date = pub_date
        self.author = author
        self.guid = guid or link
        self.read = False
        self.saved = False
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'pub_date': self.pub_date,
            'author': self.author,
            'guid': self.guid,
            'read': self.read,
            'saved': self.saved
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RSSItem':
        item = cls(
            data.get('title', ''),
            data.get('link', ''),
            data.get('description', ''),
            data.get('pub_date', ''),
            data.get('author', ''),
            data.get('guid', '')
        )
        item.read = data.get('read', False)
        item.saved = data.get('saved', False)
        return item


class RSSFeed:
    def __init__(self, url: str, title: str = '', description: str = '',
                 link: str = '', image: str = ''):
        self.url = url
        self.title = title
        self.description = description
        self.link = link
        self.image = image
        self.items: List[RSSItem] = []
        self.last_updated = None
        self.update_interval = 3600
    
    def add_item(self, item: RSSItem):
        self.items.append(item)
    
    def get_unread(self) -> List[RSSItem]:
        return [item for item in self.items if not item.read]
    
    def mark_all_read(self):
        for item in self.items:
            item.read = True
    
    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'link': self.link,
            'image': self.image,
            'items': [i.to_dict() for i in self.items],
            'last_updated': self.last_updated,
            'update_interval': self.update_interval
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RSSFeed':
        feed = cls(
            data.get('url', ''),
            data.get('title', ''),
            data.get('description', ''),
            data.get('link', ''),
            data.get('image', '')
        )
        feed.items = [RSSItem.from_dict(i) for i in data.get('items', [])]
        feed.last_updated = data.get('last_updated')
        feed.update_interval = data.get('update_interval', 3600)
        return feed


class RSSParser:
    def __init__(self):
        self.namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/',
            'content': 'http://purl.org/rss/1.0/modules/content/'
        }
    
    def parse(self, xml_content: str, url: str) -> Optional[RSSFeed]:
        try:
            root = ET.fromstring(xml_content)
            
            if root.tag == 'rss':
                return self._parse_rss(root, url)
            elif root.tag == 'feed':
                return self._parse_atom(root, url)
            elif root.tag == 'RDF':
                return self._parse_rdf(root, url)
            
        except Exception as e:
            print(f"RSS parse error: {e}")
            return None
        
        return None
    
    def _parse_rss(self, root: ET.Element, url: str) -> RSSFeed:
        channel = root.find('channel')
        if not channel:
            return None
        
        feed = RSSFeed(url)
        feed.title = self._get_text(channel, 'title')
        feed.description = self._get_text(channel, 'description')
        feed.link = self._get_text(channel, 'link')
        
        image = channel.find('image')
        if image is not None:
            feed.image = self._get_text(image, 'url')
        
        for item in channel.findall('item'):
            title = self._get_text(item, 'title')
            link = self._get_text(item, 'link')
            description = self._get_text(item, 'description')
            pub_date = self._get_text(item, 'pubDate')
            author = self._get_text(item, 'author') or self._get_text(item, 'dc:creator')
            guid = self._get_text(item, 'guid')
            
            if title and link:
                item_obj = RSSItem(title, link, description, pub_date, author, guid)
                feed.add_item(item_obj)
        
        return feed
    
    def _parse_atom(self, root: ET.Element, url: str) -> RSSFeed:
        feed = RSSFeed(url)
        feed.title = self._get_text(root, 'title')
        feed.description = self._get_text(root, 'subtitle')
        
        links = root.findall('link')
        for link in links:
            href = link.get('href')
            rel = link.get('rel', 'alternate')
            if rel == 'alternate':
                feed.link = href
                break
        
        for entry in root.findall('entry'):
            title = self._get_text(entry, 'title')
            link = ''
            links = entry.findall('link')
            for l in links:
                if l.get('rel', 'alternate') == 'alternate':
                    link = l.get('href', '')
                    break
            
            description = self._get_text(entry, 'summary') or self._get_text(entry, 'content')
            pub_date = self._get_text(entry, 'published') or self._get_text(entry, 'updated')
            author = ''
            author_elem = entry.find('author')
            if author_elem is not None:
                author = self._get_text(author_elem, 'name')
            guid = self._get_text(entry, 'id')
            
            if title:
                item_obj = RSSItem(title, link, description, pub_date, author, guid)
                feed.add_item(item_obj)
        
        return feed
    
    def _parse_rdf(self, root: ET.Element, url: str) -> RSSFeed:
        feed = RSSFeed(url)
        
        channel = root.find('channel')
        if channel is not None:
            feed.title = self._get_text(channel, 'title')
            feed.description = self._get_text(channel, 'description')
            feed.link = self._get_text(channel, 'link')
        
        for item in root.findall('item'):
            title = self._get_text(item, 'title')
            link = self._get_text(item, 'link')
            description = self._get_text(item, 'description')
            pub_date = self._get_text(item, 'dc:date')
            
            if title:
                item_obj = RSSItem(title, link, description, pub_date)
                feed.add_item(item_obj)
        
        return feed
    
    def _get_text(self, element: ET.Element, tag: str) -> str:
        found = element.find(tag)
        if found is not None and found.text:
            return found.text.strip()
        
        for ns_prefix, ns_uri in self.namespaces.items():
            found = element.find(f"{{{ns_uri}}}{tag}")
            if found is not None and found.text:
                return found.text.strip()
        
        return ''


class RSSReader:
    def __init__(self):
        self.feeds: List[RSSFeed] = []
        self.parser = RSSParser()
        self.auto_update = True
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(RSS_FILE):
            try:
                with open(RSS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.feeds = [RSSFeed.from_dict(f) for f in data.get('feeds', [])]
            except:
                pass
    
    def _save(self):
        data = {
            'feeds': [f.to_dict() for f in self.feeds]
        }
        with open(RSS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_feed(self, url: str) -> Optional[RSSFeed]:
        for feed in self.feeds:
            if feed.url == url:
                return None
        
        feed = self.fetch_feed(url)
        if feed:
            self.feeds.append(feed)
            self._save()
            return feed
        
        return None
    
    def remove_feed(self, url: str) -> bool:
        initial_len = len(self.feeds)
        self.feeds = [f for f in self.feeds if f.url != url]
        if len(self.feeds) < initial_len:
            self._save()
            return True
        return False
    
    def fetch_feed(self, url: str) -> Optional[RSSFeed]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SimpleBrowser RSS/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_content = response.read().decode('utf-8', errors='ignore')
            
            return self.parser.parse(xml_content, url)
        
        except Exception as e:
            print(f"Error fetching feed: {e}")
            return None
    
    def update_feed(self, url: str) -> Optional[RSSFeed]:
        for i, feed in enumerate(self.feeds):
            if feed.url == url:
                updated = self.fetch_feed(url)
                if updated:
                    self.feeds[i] = updated
                    self._save()
                    return updated
        return None
    
    def update_all(self) -> int:
        updated = 0
        for feed in self.feeds:
            if self.update_feed(feed.url):
                updated += 1
        return updated
    
    def get_all_items(self, limit: int = 100) -> List[RSSItem]:
        all_items = []
        for feed in self.feeds:
            all_items.extend(feed.items)
        
        all_items.sort(key=lambda x: x.pub_date, reverse=True)
        return all_items[:limit]
    
    def get_unread_items(self) -> List[RSSItem]:
        unread = []
        for feed in self.feeds:
            unread.extend(feed.get_unread())
        return unread
    
    def mark_as_read(self, guid: str):
        for feed in self.feeds:
            for item in feed.items:
                if item.guid == guid:
                    item.read = True
        self._save()
    
    def mark_all_read(self):
        for feed in self.feeds:
            feed.mark_all_read()
        self._save()
    
    def get_feeds(self) -> List[Dict]:
        return [{
            'url': f.url,
            'title': f.title or f.url,
            'description': f.description,
            'unread_count': len(f.get_unread()),
            'last_updated': f.last_updated
        } for f in self.feeds]
    
    def get_feed(self, url: str) -> Optional[RSSFeed]:
        for feed in self.feeds:
            if feed.url == url:
                return feed
        return None
    
    def search_items(self, query: str) -> List[RSSItem]:
        query = query.lower()
        results = []
        
        for feed in self.feeds:
            for item in feed.items:
                if query in item.title.lower() or query in item.description.lower():
                    results.append(item)
        
        return results
    
    def export_opml(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<opml version="2.0">\n')
            f.write('<head><title>RSS Feeds</title></head>\n')
            f.write('<body>\n')
            
            for feed in self.feeds:
                f.write(f'<outline text="{self._escape_xml(feed.title)}" ')
                f.write(f'type="rss" xmlUrl="{self._escape_xml(feed.url)}" ')
                f.write(f'htmlUrl="{self._escape_xml(feed.link)}"/>\n')
            
            f.write('</body>\n')
            f.write('</opml>\n')
    
    def import_opml(self, filepath: str):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            for outline in root.findall('.//outline'):
                xml_url = outline.get('xmlUrl')
                if xml_url:
                    self.add_feed(xml_url)
        except:
            pass
    
    def _escape_xml(self, text: str) -> str:
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        return text
    
    def get_stats(self) -> Dict:
        total_feeds = len(self.feeds)
        total_items = sum(len(f.items) for f in self.feeds)
        unread_items = sum(len(f.get_unread()) for f in self.feeds)
        
        return {
            'total_feeds': total_feeds,
            'total_items': total_items,
            'unread_items': unread_items,
            'read_items': total_items - unread_items
        }


class PodcastManager:
    def __init__(self, rss_reader: RSSReader):
        self.rss_reader = rss_reader
        self.subscriptions: List[RSSFeed] = []
        self.played_episodes: List[str] = []
        self.downloaded_episodes: List[str] = []
    
    def subscribe(self, url: str) -> Optional[RSSFeed]:
        feed = self.rss_reader.fetch_feed(url)
        if feed:
            self.subscriptions.append(feed)
            return feed
        return None
    
    def unsubscribe(self, url: str):
        self.subscriptions = [s for s in self.subscriptions if s.url != url]
    
    def get_latest_episodes(self, limit: int = 20) -> List[RSSItem]:
        episodes = []
        
        for sub in self.subscriptions:
            episodes.extend(sub.items[:5])
        
        episodes.sort(key=lambda x: x.pub_date, reverse=True)
        return episodes[:limit]
