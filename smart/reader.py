import re
import json
import os
from typing import List, Dict, Optional
from html.parser import HTMLParser

DATA_DIR = os.path.expanduser('~/.simple_browser')
READER_FILE = os.path.join(DATA_DIR, 'reader_content.json')


class ReaderContent:
    def __init__(self, title: str, content: str, url: str = ''):
        self.title = title
        self.content = content
        self.url = url
        self.author = ''
        self.date = ''
        self.site_name = ''
        self.word_count = 0
        self.reading_time = 0
        self.images: List[str] = []
        self.videos: List[str] = []
    
    def calculate_stats(self):
        self.word_count = len(self.content.split())
        self.reading_time = max(1, self.word_count // 200)
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'author': self.author,
            'date': self.date,
            'site_name': self.site_name,
            'word_count': self.word_count,
            'reading_time': self.reading_time,
            'images': self.images,
            'videos': self.videos
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReaderContent':
        content = cls(data.get('title', ''), data.get('content', ''), data.get('url', ''))
        content.author = data.get('author', '')
        content.date = data.get('date', '')
        content.site_name = data.get('site_name', '')
        content.word_count = data.get('word_count', 0)
        content.reading_time = data.get('reading_time', 0)
        content.images = data.get('images', [])
        content.videos = data.get('videos', [])
        return content


class ReaderExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.content = []
        self.current_tag = ''
        self.in_body = False
        self.in_script = False
        self.in_style = False
        self.in_nav = False
        self.in_header = False
        self.in_footer = False
        self.in_sidebar = False
        self.in_ad = False
        self.in_article = False
        self.depth = 0
        self.text_content = []
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag in ['script', 'style', 'noscript', 'iframe']:
            if tag == 'script':
                self.in_script = True
            elif tag == 'style':
                self.in_style = True
            return
        
        if tag in ['nav', 'header', 'footer', 'aside']:
            if tag == 'nav':
                self.in_nav = True
            elif tag == 'header':
                self.in_header = True
            elif tag == 'footer':
                self.in_footer = True
            elif tag == 'aside':
                self.in_sidebar = True
            return
        
        if tag in ['article', 'main']:
            self.in_article = True
        
        ad_classes = ['ad', 'ads', 'advertisement', 'promo', 'sponsored']
        class_attr = attrs_dict.get('class', '').lower()
        if any(ad in class_attr for ad in ad_classes):
            self.in_ad = True
        
        self.current_tag = tag
        self.depth += 1
    
    def handle_endtag(self, tag):
        if tag in ['script']:
            self.in_script = False
        elif tag in ['style']:
            self.in_style = False
        elif tag in ['nav']:
            self.in_nav = False
        elif tag in ['header']:
            self.in_header = False
        elif tag in ['footer']:
            self.in_footer = False
        elif tag in ['aside']:
            self.in_sidebar = False
        elif tag in ['article', 'main']:
            self.in_article = False
        elif 'ad' in tag.lower():
            self.in_ad = False
        
        if self.depth > 0:
            self.depth -= 1
        
        if tag == 'p' or tag == 'br':
            self.text_content.append('\n')
    
    def handle_data(self, data):
        if self.in_script or self.in_style or self.in_nav or self.in_header or \
           self.in_footer or self.in_sidebar or self.in_ad:
            return
        
        text = data.strip()
        if text:
            self.text_content.append(text)
    
    def get_content(self) -> str:
        return ' '.join(self.text_content)


class ReaderMode:
    def __init__(self):
        self.enabled = False
        self.theme = 'light'
        self.font_size = 18
        self.font_family = 'serif'
        self.line_height = 1.6
        self.content_width = 700
        self.saved_articles: List[ReaderContent] = []
        
        self._load()
    
    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        if os.path.exists(READER_FILE):
            try:
                with open(READER_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.saved_articles = [
                        ReaderContent.from_dict(a) for a in data.get('articles', [])
                    ]
            except:
                pass
    
    def _save(self):
        data = {
            'articles': [a.to_dict() for a in self.saved_articles]
        }
        with open(READER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def extract_content(self, html: str, url: str = '') -> ReaderContent:
        parser = ReaderExtractor()
        
        try:
            parser.feed(html)
        except:
            pass
        
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1) if title_match else 'Untitled'
        
        title = re.sub(r'\s*[-|]\s*.*$', '', title)
        
        author_match = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        author = author_match.group(1) if author_match else ''
        
        date_match = re.search(r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        date = date_match.group(1) if date_match else ''
        
        site_name_match = re.search(r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        site_name = site_name_match.group(1) if site_name_match else ''
        
        images = re.findall(r'<img[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        
        videos = re.findall(r'<video[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        
        content_text = parser.get_content()
        
        content_text = re.sub(r'\n{3,}', '\n\n', content_text)
        content_text = content_text.strip()
        
        content = ReaderContent(title, content_text, url)
        content.author = author
        content.date = date
        content.site_name = site_name
        content.images = images[:10]
        content.videos = videos
        content.calculate_stats()
        
        return content
    
    def format_html(self, content: ReaderContent) -> str:
        theme_colors = {
            'light': {'bg': '#ffffff', 'text': '#333333', 'link': '#0066cc'},
            'dark': {'bg': '#1a1a1a', 'text': '#e0e0e0', 'link': '#66b3ff'},
            'sepia': {'bg': '#f4ecd8', 'text': '#5b4636', 'link': '#8b4513'}
        }
        
        colors = theme_colors.get(self.theme, theme_colors['light'])
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: {self.font_family};
            font-size: {self.font_size}px;
            line-height: {self.line_height};
            max-width: {self.content_width}px;
            margin: 0 auto;
            padding: 20px;
            background-color: {colors['bg']};
            color: {colors['text']};
        }}
        h1 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        .content {{
            text-align: justify;
        }}
        a {{
            color: {colors['link']};
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 10px 0;
        }}
        blockquote {{
            border-left: 3px solid #ccc;
            padding-left: 15px;
            margin-left: 0;
            font-style: italic;
        }}
        pre, code {{
            background-color: rgba(0,0,0,0.1);
            padding: 2px 5px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <h1>{content.title}</h1>
    <div class="meta">
        {f'<span class="author">{content.author}</span>' if content.author else ''}
        {f'<span class="date">{content.date[:10]}</span>' if content.date else ''}
        {f'<span class="site">{content.site_name}</span>' if content.site_name else ''}
    </div>
    <div class="content">
        {self._format_text(content.content)}
    </div>
    <div class="footer">
        <p>Estimated reading time: {content.reading_time} minutes</p>
    </div>
</body>
</html>
        '''
        return html
    
    def _format_text(self, text: str) -> str:
        paragraphs = text.split('\n\n')
        
        formatted = []
        for p in paragraphs:
            p = p.strip()
            if p:
                formatted.append(f'<p>{p}</p>')
        
        return '\n'.join(formatted)
    
    def save_article(self, content: ReaderContent):
        for saved in self.saved_articles:
            if saved.url == content.url:
                return
        
        self.saved_articles.insert(0, content)
        self.saved_articles = self.saved_articles[:50]
        self._save()
    
    def remove_article(self, url: str) -> bool:
        initial_len = len(self.saved_articles)
        self.saved_articles = [a for a in self.saved_articles if a.url != url]
        if len(self.saved_articles) < initial_len:
            self._save()
            return True
        return False
    
    def get_saved_articles(self) -> List[ReaderContent]:
        return self.saved_articles
    
    def set_theme(self, theme: str):
        if theme in ['light', 'dark', 'sepia']:
            self.theme = theme
    
    def set_font_size(self, size: int):
        self.font_size = max(12, min(32, size))
    
    def set_font_family(self, family: str):
        self.font_family = family
    
    def set_line_height(self, height: float):
        self.line_height = max(1.0, min(2.5, height))
    
    def set_content_width(self, width: int):
        self.content_width = max(400, min(1200, width))
    
    def toggle(self):
        self.enabled = not self.enabled
    
    def get_settings(self) -> Dict:
        return {
            'enabled': self.enabled,
            'theme': self.theme,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'line_height': self.line_height,
            'content_width': self.content_width
        }


class TextSimplifier:
    def __init__(self):
        self.simplification_level = 0
    
    def simplify(self, text: str, level: int = 1) -> str:
        if level == 0:
            return text
        
        text = re.sub(r'\([^)]*\)', '', text)
        
        text = re.sub(r'\s{2,}', ' ', text)
        
        if level >= 2:
            complex_words = {
                'approximately': 'about',
                'utilize': 'use',
                'subsequently': 'later',
                'nevertheless': 'however',
                'furthermore': 'also',
                'consequently': 'so',
                'demonstrate': 'show',
                'facilitate': 'help',
                'implement': 'do',
                'modification': 'change'
            }
            for word, simple in complex_words.items():
                text = re.sub(r'\b' + word + r'\b', simple, text, flags=re.IGNORECASE)
        
        return text.strip()
