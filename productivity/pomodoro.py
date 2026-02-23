import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, List, Optional

try:
    from android import mActivity
    from android.os import Vibrator
    ANDROID_VIBRATE = True
except:
    ANDROID_VIBRATE = False


class PomodoroState(Enum):
    IDLE = 'idle'
    WORK = 'work'
    SHORT_BREAK = 'short_break'
    LONG_BREAK = 'long_break'
    PAUSED = 'paused'


class PomodoroSession:
    def __init__(self, session_type: str, duration: int):
        self.session_type = session_type
        self.duration = duration
        self.start_time = None
        self.end_time = None
        self.completed = False
    
    def start(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=self.duration)
    
    def complete(self):
        self.completed = True
    
    def get_remaining_time(self) -> int:
        if not self.start_time:
            return self.duration
        remaining = (self.end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))


class PomodoroTimer:
    def __init__(self):
        self.work_duration = 25 * 60
        self.short_break_duration = 5 * 60
        self.long_break_duration = 15 * 60
        self.sessions_until_long_break = 4
        
        self.state = PomodoroState.IDLE
        self.current_session: Optional[PomodoroSession] = None
        self.session_count = 0
        self.total_sessions_completed = 0
        
        self.running = False
        self.paused = False
        self.pause_time = None
        self.total_paused_time = 0
        
        self.start_callbacks: List[Callable] = []
        self.complete_callbacks: List[Callable] = []
        self.tick_callbacks: List[Callable] = []
        
        self.sessions_history: List[dict] = []
    
    def start_work(self):
        self.current_session = PomodoroSession('work', self.work_duration)
        self.current_session.start()
        self.state = PomodoroState.WORK
        self.running = True
        self.paused = False
        self._notify_start()
    
    def start_short_break(self):
        self.current_session = PomodoroSession('short_break', self.short_break_duration)
        self.current_session.start()
        self.state = PomodoroState.SHORT_BREAK
        self.running = True
        self.paused = False
        self._notify_start()
    
    def start_long_break(self):
        self.current_session = PomodoroSession('long_break', self.long_break_duration)
        self.current_session.start()
        self.state = PomodoroState.LONG_BREAK
        self.running = True
        self.paused = False
        self._notify_start()
    
    def pause(self):
        if self.running and not self.paused:
            self.paused = True
            self.pause_time = datetime.now()
            self.state = PomodoroState.PAUSED
    
    def resume(self):
        if self.paused and self.pause_time:
            paused_duration = (datetime.now() - self.pause_time).total_seconds()
            self.total_paused_time += paused_duration
            self.paused = False
            self.pause_time = None
            
            if self.current_session:
                if self.state == PomodoroState.WORK:
                    self.state = PomodoroState.WORK
                elif self.state == PomodoroState.SHORT_BREAK:
                    self.state = PomodoroState.SHORT_BREAK
                elif self.state == PomodoroState.LONG_BREAK:
                    self.state = PomodoroState.LONG_BREAK
    
    def stop(self):
        self.running = False
        self.paused = False
        self.state = PomodoroState.IDLE
        self.current_session = None
        self.total_paused_time = 0
    
    def skip(self):
        if self.current_session:
            self._complete_session()
    
    def reset(self):
        self.stop()
        self.session_count = 0
        self.total_sessions_completed = 0
        self.sessions_history = []
    
    def tick(self) -> bool:
        if not self.running or self.paused or not self.current_session:
            return False
        
        remaining = self.current_session.get_remaining_time()
        
        if remaining <= 0:
            self._complete_session()
            return True
        
        self._notify_tick(remaining)
        return True
    
    def _complete_session(self):
        if self.current_session:
            self.current_session.complete()
            
            session_data = {
                'type': self.current_session.session_type,
                'duration': self.current_session.duration,
                'completed_at': datetime.now().isoformat()
            }
            self.sessions_history.append(session_data)
            
            if self.current_session.session_type == 'work':
                self.session_count += 1
                self.total_sessions_completed += 1
            
            self._notify_complete()
            
            if self.current_session.session_type == 'work':
                if self.session_count >= self.sessions_until_long_break:
                    self.start_long_break()
                    self.session_count = 0
                else:
                    self.start_short_break()
            else:
                self.start_work()
    
    def get_time_left(self) -> int:
        if not self.current_session:
            return self.work_duration
        return self.current_session.get_remaining_time()
    
    def get_formatted_time(self) -> str:
        seconds = self.get_time_left()
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"
    
    def get_progress(self) -> float:
        if not self.current_session:
            return 0
        elapsed = self.current_session.duration - self.get_time_left()
        return (elapsed / self.current_session.duration) * 100
    
    def get_state(self) -> str:
        return self.state.value
    
    def get_stats(self) -> dict:
        today = datetime.now().date()
        today_sessions = [
            s for s in self.sessions_history
            if datetime.fromisoformat(s['completed_at']).date() == today
            and s['type'] == 'work'
        ]
        
        return {
            'state': self.state.value,
            'session_count': self.session_count,
            'total_sessions': self.total_sessions_completed,
            'today_sessions': len(today_sessions),
            'time_left': self.get_formatted_time(),
            'progress': self.get_progress(),
            'is_running': self.running,
            'is_paused': self.paused
        }
    
    def get_weekly_stats(self) -> dict:
        week_ago = datetime.now() - timedelta(days=7)
        weekly_sessions = [
            s for s in self.sessions_history
            if datetime.fromisoformat(s['completed_at']) > week_ago
            and s['type'] == 'work'
        ]
        
        daily_stats = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date()
            count = len([
 in weekly_sessions                s for s
                if datetime.fromisoformat(s['completed_at']).date() == date
            ])
            daily_stats[date.isoformat()] = count
        
        return {
            'total_sessions': len(weekly_sessions),
            'daily_stats': daily_stats,
            'average_per_day': len(weekly_sessions) / 7
        }
    
    def set_work_duration(self, minutes: int):
        self.work_duration = minutes * 60
    
    def set_short_break_duration(self, minutes: int):
        self.short_break_duration = minutes * 60
    
    def set_long_break_duration(self, minutes: int):
        self.long_break_duration = minutes * 60
    
    def set_sessions_until_long_break(self, count: int):
        self.sessions_until_long_break = count
    
    def on_start(self, callback: Callable):
        self.start_callbacks.append(callback)
    
    def on_complete(self, callback: Callable):
        self.complete_callbacks.append(callback)
    
    def on_tick(self, callback: Callable):
        self.tick_callbacks.append(callback)
    
    def _notify_start(self):
        for callback in self.start_callbacks:
            try:
                callback(self.state.value)
            except:
                pass
        self._vibrate()
    
    def _notify_complete(self):
        for callback in self.complete_callbacks:
            try:
                callback(self.current_session.session_type)
            except:
                pass
        self._vibrate()
    
    def _notify_tick(self, remaining: int):
        for callback in self.tick_callbacks:
            try:
                callback(remaining)
            except:
                pass
    
    def _vibrate(self):
        if ANDROID_VIBRATE:
            try:
                vibrator = mActivity.getSystemService('vibrator')
                if vibrator:
                    vibrator.vibrate(500)
            except:
                pass


class FocusMode:
    def __init__(self):
        self.enabled = False
        self.blocked_apps = []
        self.start_time = None
        self.duration = 0
    
    def enable(self, duration: int = 0):
        self.enabled = True
        self.start_time = datetime.now()
        self.duration = duration
    
    def disable(self):
        self.enabled = False
        self.start_time = None
        self.duration = 0
    
    def get_remaining_time(self) -> int:
        if not self.enabled or not self.start_time:
            return 0
        
        if self.duration == 0:
            return 0
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        remaining = self.duration - elapsed
        return max(0, int(remaining))


class SessionLogger:
    def __init__(self):
        self.sessions: List[dict] = []
    
    def log_session(self, session_type: str, duration: int, completed: bool):
        self.sessions.append({
            'type': session_type,
            'duration': duration,
            'completed': completed,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_sessions(self, days: int = 7) -> List[dict]:
        cutoff = datetime.now() - timedelta(days=days)
        return [
            s for s in self.sessions
            if datetime.fromisoformat(s['timestamp']) > cutoff
        ]
    
    def get_total_focus_time(self, days: int = 7) -> int:
        sessions = self.get_sessions(days)
        return sum(
            s['duration'] for s in sessions
            if s['type'] == 'work' and s['completed']
        )
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['type', 'duration', 'completed', 'timestamp'])
            for s in self.sessions:
                writer.writerow([s['type'], s['duration'], s['completed'], s['timestamp']])
