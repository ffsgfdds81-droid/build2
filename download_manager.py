import os
import uuid
import hashlib
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Callable

try:
    from jnius import autoclass
    AndroidDownloads = autoclass('android.app.DownloadManager')
    ANDROID_AVAILABLE = True
except:
    ANDROID_AVAILABLE = False


class DownloadState(Enum):
    PENDING = 'pending'
    DOWNLOADING = 'downloading'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Download:
    def __init__(self, url: str, filename: str, save_path: str = '',
                 total_bytes: int = 0, mime_type: str = 'application/octet-stream'):
        self.id = str(uuid.uuid4())
        self.url = url
        self.filename = filename
        self.save_path = save_path
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.mime_type = mime_type
        self.state = DownloadState.PENDING
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.speed = 0
        self.progress = 0
    
    def update_progress(self, downloaded: int, speed: int = 0):
        self.downloaded_bytes = downloaded
        self.speed = speed
        if self.total_bytes > 0:
            self.progress = (downloaded / self.total_bytes) * 100
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'url': self.url,
            'filename': self.filename,
            'save_path': self.save_path,
            'total_bytes': self.total_bytes,
            'downloaded_bytes': self.downloaded_bytes,
            'mime_type': self.mime_type,
            'state': self.state.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'speed': self.speed,
            'progress': self.progress
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Download':
        download = cls(data['url'], data['filename'], data.get('save_path', ''),
                      data.get('total_bytes', 0), data.get('mime_type', 'application/octet-stream'))
        download.id = data.get('id', download.id)
        download.downloaded_bytes = data.get('downloaded_bytes', 0)
        download.state = DownloadState(data.get('state', 'pending'))
        download.created_at = data.get('created_at', download.created_at)
        download.started_at = data.get('started_at')
        download.completed_at = data.get('completed_at')
        download.error_message = data.get('error_message')
        download.speed = data.get('speed', 0)
        download.progress = data.get('progress', 0)
        return download


class DownloadManager:
    def __init__(self, download_dir: str = None):
        if download_dir is None:
            download_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'SimpleBrowser')
        
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        self.downloads: List[Download] = []
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
    
    def add_download(self, url: str, filename: str = None, 
                    save_path: str = None, mime_type: str = 'application/octet-stream') -> Download:
        if filename is None:
            filename = url.split('/')[-1] or 'download'
        
        if save_path is None:
            save_path = os.path.join(self.download_dir, filename)
        
        download = Download(url, filename, save_path, mime_type=mime_type)
        self.downloads.append(download)
        
        self._notify_progress(download)
        return download
    
    def start_download(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download:
            return False
        
        download.state = DownloadState.DOWNLOADING
        download.started_at = datetime.now().isoformat()
        return True
    
    def pause_download(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download or download.state != DownloadState.DOWNLOADING:
            return False
        
        download.state = DownloadState.PAUSED
        return True
    
    def resume_download(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download or download.state != DownloadState.PAUSED:
            return False
        
        download.state = DownloadState.DOWNLOADING
        return True
    
    def cancel_download(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download:
            return False
        
        download.state = DownloadState.CANCELLED
        return True
    
    def remove_download(self, download_id: str) -> bool:
        for i, d in enumerate(self.downloads):
            if d.id == download_id:
                self.downloads.pop(i)
                return True
        return False
    
    def get_download(self, download_id: str) -> Optional[Download]:
        for d in self.downloads:
            if d.id == download_id:
                return d
        return None
    
    def get_all_downloads(self) -> List[Download]:
        return self.downloads
    
    def get_active_downloads(self) -> List[Download]:
        return [d for d in self.downloads 
                if d.state == DownloadState.DOWNLOADING 
                or d.state == DownloadState.PENDING]
    
    def get_completed_downloads(self) -> List[Download]:
        return [d for d in self.downloads if d.state == DownloadState.COMPLETED]
    
    def get_downloads_by_url(self, url: str) -> List[Download]:
        return [d for d in self.downloads if d.url == url]
    
    def is_downloading(self, url: str) -> bool:
        return any(d.url == url and d.state == DownloadState.DOWNLOADING 
                  for d in self.downloads)
    
    def get_total_size(self) -> int:
        return sum(d.total_bytes for d in self.downloads)
    
    def get_downloaded_size(self) -> int:
        return sum(d.downloaded_bytes for d in self.downloads)
    
    def on_progress(self, callback: Callable):
        self.progress_callbacks.append(callback)
    
    def on_complete(self, callback: Callable):
        self.completion_callbacks.append(callback)
    
    def _notify_progress(self, download: Download):
        for callback in self.progress_callbacks:
            try:
                callback(download)
            except:
                pass
    
    def _notify_complete(self, download: Download):
        for callback in self.completion_callbacks:
            try:
                callback(download)
            except:
                pass
    
    def open_download(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download or download.state != DownloadState.COMPLETED:
            return False
        
        if os.path.exists(download.save_path):
            import subprocess
            try:
                subprocess.Popen(['xdg-open', download.save_path])
                return True
            except:
                pass
        return False
    
    def delete_file(self, download_id: str) -> bool:
        download = self.get_download(download_id)
        if not download:
            return False
        
        if os.path.exists(download.save_path):
            try:
                os.remove(download.save_path)
                return True
            except:
                pass
        return False
    
    def clear_completed(self):
        self.downloads = [d for d in self.downloads 
                         if d.state != DownloadState.COMPLETED]
    
    def clear_all(self):
        self.downloads = []
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        return {
            'video': ['mp4', 'mkv', 'avi', 'mov', 'webm'],
            'audio': ['mp3', 'wav', 'ogg', 'flac', 'aac'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'],
            'document': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
            'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
            'executable': ['exe', 'msi', 'apk', 'deb', 'rpm']
        }
    
    def get_file_icon(self, filename: str) -> str:
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        formats = self.get_supported_formats()
        for category, extensions in formats.items():
            if ext in extensions:
                return category
        return 'file'
    
    def format_size(self, bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"
    
    def format_speed(self, bytes_per_sec: int) -> str:
        return self.format_size(bytes_per_sec) + '/s'
    
    def get_history(self, limit: int = 100) -> List[Download]:
        sorted_downloads = sorted(self.downloads, 
                                  key=lambda x: x.created_at, 
                                  reverse=True)
        return sorted_downloads[:limit]
