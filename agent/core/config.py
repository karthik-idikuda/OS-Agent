"""
Configuration and Settings for Voice Agent
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


@dataclass
class OllamaConfig:
    """Ollama LLM configuration - set to None to disable"""
    base_url: Optional[str] = None             # e.g., "http://localhost:11434"
    planner_model: Optional[str] = None        # e.g., "llama3.2:3b"
    vision_model: Optional[str] = None         # e.g., "llava:7b"
    timeout: int = 60
    temperature: float = 0.1                   # Low for deterministic planning
    
    @property
    def is_enabled(self) -> bool:
        """Check if Ollama is configured"""
        return self.base_url is not None and self.planner_model is not None


@dataclass
class VoiceConfig:
    """Voice interface configuration"""
    tts_voice: str = "en-US-AriaNeural"      # Edge TTS voice
    tts_rate: str = "+10%"                   # Speech rate
    listen_timeout: int = 8                  # Seconds to wait for speech
    phrase_time_limit: int = 15              # Max phrase duration
    calibration_duration: float = 0.5        # Ambient noise calibration


@dataclass
class ExecutorConfig:
    """Action executor configuration"""
    click_delay: float = 0.1                 # Delay after clicks
    type_interval: float = 0.02              # Interval between keystrokes
    action_timeout: int = 30                 # Max time for action completion
    max_retries: int = 3                     # Retries per action
    safe_mode: bool = True                   # Require confirmation for risky actions


@dataclass
class AgentConfig:
    """Main agent configuration"""
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    
    # Behavior
    max_plan_steps: int = 10                 # Max steps in a plan
    conversation_memory: int = 20            # Messages to remember
    screenshot_retention_days: int = 7       # Auto-delete old screenshots
    
    # Debug
    verbose: bool = False
    save_screenshots: bool = True


# Global config instance
config = AgentConfig()


# System commands mapping (macOS)
SYSTEM_COMMANDS = {
    # WiFi
    "wifi_on": "networksetup -setairportpower en0 on",
    "wifi_off": "networksetup -setairportpower en0 off",
    "wifi_status": "networksetup -getairportpower en0",
    
    # Bluetooth (requires blueutil: brew install blueutil)
    "bluetooth_on": "blueutil --power 1",
    "bluetooth_off": "blueutil --power 0",
    "bluetooth_status": "blueutil --power",
    
    # Volume
    "volume_up": "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 10)'",
    "volume_down": "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 10)'",
    "volume_mute": "osascript -e 'set volume output muted true'",
    "volume_unmute": "osascript -e 'set volume output muted false'",
    "volume_set": "osascript -e 'set volume output volume {level}'",  # 0-100
    
    # Brightness (requires brightness: brew install brightness)
    "brightness_up": "brightness 0.1 +",
    "brightness_down": "brightness 0.1 -",
    
    # Screen
    "screenshot": "screencapture -x {path}",
    "lock_screen": "pmset displaysleepnow",
    
    # System
    "sleep": "pmset sleepnow",
    "open_app": "open -a '{app}'",
    "close_app": "osascript -e 'quit app \"{app}\"'",
    "list_apps": "ls /Applications",
}

# App aliases for natural language
APP_ALIASES = {
    "chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "slack": "Slack",
    "discord": "Discord",
    "spotify": "Spotify",
    "music": "Music",
    "notes": "Notes",
    "reminders": "Reminders",
    "calendar": "Calendar",
    "mail": "Mail",
    "messages": "Messages",
    "finder": "Finder",
    "terminal": "Terminal",
    "vscode": "Visual Studio Code",
    "code": "Visual Studio Code",
    "calculator": "Calculator",
    "settings": "System Preferences",
    "preferences": "System Preferences",
    "photos": "Photos",
    "youtube": "Safari",  # Opens in browser
}
