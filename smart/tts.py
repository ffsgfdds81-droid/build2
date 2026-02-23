import os
import threading
from typing import Optional, Callable, List
from enum import Enum

try:
    from jnius import autoclass, cast
    from android import mActivity
    ANDROID = True
except:
    ANDROID = False


class TTSState(Enum):
    IDLE = 'idle'
    SPEAKING = 'speaking'
    PAUSED = 'paused'
    ERROR = 'error'


class TTSVoice:
    def __init__(self, name: str, language: str, country: str = ''):
        self.name = name
        self.language = language
        self.country = country
        self.id = f"{language}_{country}_{name}" if country else f"{language}_{name}"


class TTSManager:
    def __init__(self):
        self.state = TTSState.IDLE
        self.speaking = False
        self.paused = False
        
        self.rate = 1.0
        self.pitch = 1.0
        self.volume = 1.0
        
        self.current_text = ''
        self.current_position = 0
        
        self.available_voices: List[TTSVoice] = []
        self.selected_voice: Optional[TTSVoice] = None
        
        self.on_start_callbacks: List[Callable] = []
        self.on_complete_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        self.on_progress_callbacks: List[Callable] = []
        
        self.queue: List[str] = []
        self.queue_enabled = True
        
        self._init_android_tts()
    
    def _init_android_tts(self):
        if ANDROID:
            try:
                self.tts = None
                self.locale = None
            except:
                pass
    
    def speak(self, text: str, interrupt: bool = True) -> bool:
        if not text:
            return False
        
        if interrupt:
            self.stop()
        
        self.current_text = text
        self.current_position = 0
        
        if self.queue_enabled:
            self.queue.append(text)
            if len(self.queue) == 1:
                return self._speak_current()
        else:
            return self._speak_text(text)
        
        return True
    
    def _speak_current(self):
        if not self.queue:
            return False
        
        text = self.queue[0]
        return self._speak_text(text)
    
    def _speak_text(self, text: str) -> bool:
        if ANDROID:
            return self._speak_android(text)
        
        self.speaking = True
        self.state = TTSState.SPEAKING
        self._notify_start()
        return True
    
    def _speak_android(self, text: str) -> bool:
        try:
            Locale = autoclass('java.util.Locale')
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            
            if self.tts is None:
                self.tts = TextToSpeech(mActivity, None)
                self.tts.setLanguage(Locale.US)
            
            self.tts.setSpeechRate(self.rate)
            self.tts.setPitch(self.pitch)
            
            result = self.tts.speak(text, 1, None, 'utteranceId')
            
            self.speaking = True
            self.state = TTSState.SPEAKING
            self._notify_start()
            
            return result == 0
            
        except Exception as e:
            self.state = TTSState.ERROR
            self._notify_error(str(e))
            return False
    
    def stop(self):
        if ANDROID:
            try:
                if self.tts:
                    self.tts.stop()
            except:
                pass
        
        self.queue.clear()
        self.speaking = False
        self.paused = False
        self.state = TTSState.IDLE
        self.current_text = ''
        self.current_position = 0
    
    def pause(self):
        if self.speaking and not self.paused:
            self.paused = True
            self.state = TTSState.PAUSED
    
    def resume(self):
        if self.paused:
            self.paused = False
            self.state = TTSState.SPEAKING
    
    def get_voices(self) -> List[TTSVoice]:
        if not self.available_voices:
            self.available_voices = [
                TTSVoice('English US', 'en', 'US'),
                TTSVoice('English UK', 'en', 'GB'),
                TTSVoice('Russian', 'ru', 'RU'),
                TTSVoice('Spanish', 'es', 'ES'),
                TTSVoice('French', 'fr', 'FR'),
                TTSVoice('German', 'de', 'DE'),
                TTSVoice('Chinese', 'zh', 'CN'),
                TTSVoice('Japanese', 'ja', 'JP'),
                TTSVoice('Korean', 'ko', 'KR'),
            ]
        return self.available_voices
    
    def set_voice(self, voice_id: str):
        voices = self.get_voices()
        for voice in voices:
            if voice.id == voice_id:
                self.selected_voice = voice
                break
    
    def set_rate(self, rate: float):
        self.rate = max(0.5, min(2.0, rate))
        if ANDROID and self.tts:
            try:
                self.tts.setSpeechRate(self.rate)
            except:
                pass
    
    def set_pitch(self, pitch: float):
        self.pitch = max(0.5, min(2.0, pitch))
        if ANDROID and self.tts:
            try:
                self.tts.setPitch(self.pitch)
            except:
                pass
    
    def set_volume(self, volume: float):
        self.volume = max(0.0, min(1.0, volume))
    
    def is_speaking(self) -> bool:
        return self.speaking
    
    def is_paused(self) -> bool:
        return self.paused
    
    def get_state(self) -> str:
        return self.state.value
    
    def get_progress(self) -> float:
        if not self.current_text:
            return 0
        return (self.current_position / len(self.current_text)) * 100
    
    def on_start(self, callback: Callable):
        self.on_start_callbacks.append(callback)
    
    def on_complete(self, callback: Callable):
        self.on_complete_callbacks.append(callback)
    
    def on_error(self, callback: Callable):
        self.on_error_callbacks.append(callback)
    
    def on_progress(self, callback: Callable):
        self.on_progress_callbacks.append(callback)
    
    def _notify_start(self):
        for callback in self.on_start_callbacks:
            try:
                callback(self.current_text)
            except:
                pass
    
    def _notify_complete(self):
        for callback in self.on_complete_callbacks:
            try:
                callback()
            except:
                pass
    
    def _notify_error(self, error: str):
        for callback in self.on_error_callbacks:
            try:
                callback(error)
            except:
                pass
    
    def _notify_progress(self, position: int, length: int):
        for callback in self.on_progress_callbacks:
            try:
                callback(position, length)
            except:
                pass
    
    def speak_text_selection(self, text: str, url: str = '') -> str:
        processed = self._preprocess_text(text)
        return processed
    
    def _preprocess_text(self, text: str) -> str:
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        text = text.replace('&', 'and')
        text = text.replace('@', 'at')
        text = text.replace('#', 'number')
        text = text.replace('%', 'percent')
        
        return text
    
    def get_language_for_url(self, url: str) -> Optional[str]:
        domain = url.split('/')[2] if '://' in url else url.split('/')[0]
        
        language_map = {
            '.ru': 'ru_RU',
            '.ua': 'uk_UA',
            '.by': 'be_BY',
            '.kz': 'kk_KZ',
            '.cn': 'zh_CN',
            '.jp': 'ja_JP',
            '.kr': 'ko_KR',
            '.de': 'de_DE',
            '.fr': 'fr_FR',
            '.es': 'es_ES',
            '.it': 'it_IT',
            '.br': 'pt_BR',
        }
        
        for ext, lang in language_map.items():
            if domain.endswith(ext):
                return lang
        
        return None
    
    def speak_page_title(self, title: str) -> bool:
        return self.speak(f"Page: {title}")
    
    def speak_url(self, url: str) -> bool:
        domain = url.split('/')[2] if '://' in url else url.split('/')[0]
        return self.speak(f"URL: {domain}")
    
    def set_queue_enabled(self, enabled: bool):
        self.queue_enabled = enabled
    
    def skip(self):
        if self.queue:
            self.queue.pop(0)
            self._speak_current()


class WebReader:
    def __init__(self, tts: TTSManager):
        self.tts = tts
        self.extracted_text = ''
        self.reading_mode = False
    
    def extract_text_from_html(self, html: str) -> str:
        import re
        
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        text = re.sub(r'<[^>]+>', ' ', text)
        
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        self.extracted_text = text
        return text
    
    def read_page(self, html: str) -> bool:
        text = self.extract_text_from_html(html)
        
        if len(text) > 5000:
            text = text[:5000] + "... Content truncated."
        
        self.reading_mode = True
        return self.tts.speak(text)
    
    def stop_reading(self):
        self.tts.stop()
        self.reading_mode = False
    
    def get_extracted_text(self) -> str:
        return self.extracted_text
    
    def get_word_count(self) -> int:
        return len(self.extracted_text.split())
    
    def get_estimated_read_time(self) -> int:
        words = self.get_word_count()
        return (words / 200) * 60


class VoiceInput:
    def __init__(self):
        self.listening = False
        self.recognition = None
    
    def start_listening(self) -> bool:
        self.listening = True
        return True
    
    def stop_listening(self) -> str:
        self.listening = False
        return ''
    
    def is_listening(self) -> bool:
        return self.listening
    
    def on_result(self, callback: Callable):
        pass
