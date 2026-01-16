"""
Command Registry - Direct commands that execute instantly without AI planning

This module provides a registry of commands that can be executed immediately
when the user says something like "turn on wifi" or "open safari". These bypass
the AI planning system for faster response.
"""
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Categories of direct commands"""
    SYSTEM = "system"        # WiFi, Bluetooth, Volume, Brightness
    APP = "app"              # Open/Close applications
    NAVIGATION = "navigation"  # URL, file access
    KEYBOARD = "keyboard"    # Key presses, shortcuts
    MEDIA = "media"          # Play, pause, skip


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    message: str
    output: Optional[str] = None
    error: Optional[str] = None


class DirectCommand(ABC):
    """Base class for direct commands"""
    
    def __init__(
        self,
        name: str,
        category: CommandCategory,
        description: str = "",
        requires_param: bool = False,
        param_name: Optional[str] = None
    ):
        self.name = name
        self.category = category
        self.description = description
        self.requires_param = requires_param
        self.param_name = param_name
    
    @abstractmethod
    def execute(self, params: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Execute the command"""
        pass
    
    def __repr__(self):
        return f"DirectCommand({self.name})"


class SystemCommand(DirectCommand):
    """System commands executed via shell"""
    
    def __init__(
        self,
        name: str,
        shell_command: str,
        description: str = "",
        requires_param: bool = False,
        param_name: Optional[str] = None,
        success_message: Optional[str] = None
    ):
        super().__init__(name, CommandCategory.SYSTEM, description, requires_param, param_name)
        self.shell_command = shell_command
        self.success_message = success_message or f"{name} executed"
    
    def execute(self, params: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Execute shell command"""
        try:
            # Format command with params
            cmd = self.shell_command
            if params:
                cmd = cmd.format(**params)
            
            # Execute
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return CommandResult(
                    success=True,
                    message=self.success_message,
                    output=result.stdout.strip()
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"Command failed: {self.name}",
                    error=result.stderr.strip()
                )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                message=f"Command timed out: {self.name}",
                error="Timeout"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error executing {self.name}",
                error=str(e)
            )


class AppCommand(DirectCommand):
    """Application control commands"""
    
    def __init__(
        self,
        name: str,
        app_name: str,
        action: str = "open",  # open, close, toggle
        description: str = ""
    ):
        super().__init__(name, CommandCategory.APP, description)
        self.app_name = app_name
        self.action = action
    
    def execute(self, params: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Open or close the application"""
        try:
            if self.action == "open":
                cmd = f'open -a "{self.app_name}"'
                success_msg = f"Opened {self.app_name}"
            elif self.action == "close":
                cmd = f'osascript -e \'quit app "{self.app_name}"\''
                success_msg = f"Closed {self.app_name}"
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown action: {self.action}",
                    error="Invalid action"
                )
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return CommandResult(
                success=result.returncode == 0,
                message=success_msg if result.returncode == 0 else f"Failed to {self.action} {self.app_name}",
                error=result.stderr.strip() if result.returncode != 0 else None
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error with {self.app_name}",
                error=str(e)
            )


class NavigationCommand(DirectCommand):
    """URL and file navigation commands"""
    
    def __init__(
        self,
        name: str,
        url: Optional[str] = None,
        description: str = ""
    ):
        super().__init__(
            name,
            CommandCategory.NAVIGATION,
            description,
            requires_param=url is None,
            param_name="url" if url is None else None
        )
        self.url = url
    
    def execute(self, params: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Open URL in default browser"""
        try:
            url = self.url or (params.get("url") if params else None)
            if not url:
                return CommandResult(
                    success=False,
                    message="No URL provided",
                    error="URL required"
                )
            
            # Add protocol if missing
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            result = subprocess.run(
                f'open "{url}"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return CommandResult(
                success=result.returncode == 0,
                message=f"Opened {url}",
                error=result.stderr.strip() if result.returncode != 0 else None
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to open URL",
                error=str(e)
            )


class CommandRegistry:
    """
    Registry of all direct commands.
    
    Direct commands are matched against user input and executed immediately
    without requiring AI planning. This provides fast response for common
    system operations.
    
    Example:
        registry = CommandRegistry()
        result = registry.execute("turn on wifi")
        # WiFi is turned on immediately
    """
    
    def __init__(self):
        self.commands: Dict[str, DirectCommand] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command name
        self._register_defaults()
    
    def _register_defaults(self):
        """Register all default commands"""
        
        # =================================================================
        # WiFi Commands
        # =================================================================
        self.register(
            "wifi_on",
            SystemCommand(
                "wifi_on",
                "networksetup -setairportpower en0 on",
                "Turn on WiFi",
                success_message="WiFi enabled"
            ),
            aliases=["turn on wifi", "enable wifi", "wifi on", "start wifi", "activate wifi"]
        )
        
        self.register(
            "wifi_off",
            SystemCommand(
                "wifi_off",
                "networksetup -setairportpower en0 off",
                "Turn off WiFi",
                success_message="WiFi disabled"
            ),
            aliases=["turn off wifi", "disable wifi", "wifi off", "stop wifi", "deactivate wifi"]
        )
        
        # =================================================================
        # Bluetooth Commands
        # =================================================================
        self.register(
            "bluetooth_on",
            SystemCommand(
                "bluetooth_on",
                "blueutil --power 1",
                "Turn on Bluetooth",
                success_message="Bluetooth enabled"
            ),
            aliases=["turn on bluetooth", "enable bluetooth", "bluetooth on", "start bluetooth"]
        )
        
        self.register(
            "bluetooth_off",
            SystemCommand(
                "bluetooth_off",
                "blueutil --power 0",
                "Turn off Bluetooth",
                success_message="Bluetooth disabled"
            ),
            aliases=["turn off bluetooth", "disable bluetooth", "bluetooth off", "stop bluetooth"]
        )
        
        # =================================================================
        # Volume Commands
        # =================================================================
        self.register(
            "mute",
            SystemCommand(
                "mute",
                "osascript -e 'set volume output muted true'",
                "Mute audio",
                success_message="Audio muted"
            ),
            aliases=["mute", "mute audio", "mute sound", "silence", "be quiet"]
        )
        
        self.register(
            "unmute",
            SystemCommand(
                "unmute",
                "osascript -e 'set volume output muted false'",
                "Unmute audio",
                success_message="Audio unmuted"
            ),
            aliases=["unmute", "unmute audio", "unmute sound", "turn on sound"]
        )
        
        self.register(
            "volume_up",
            SystemCommand(
                "volume_up",
                "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 10)'",
                "Increase volume",
                success_message="Volume increased"
            ),
            aliases=["volume up", "increase volume", "louder", "turn up volume", "raise volume"]
        )
        
        self.register(
            "volume_down",
            SystemCommand(
                "volume_down",
                "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 10)'",
                "Decrease volume",
                success_message="Volume decreased"
            ),
            aliases=["volume down", "decrease volume", "quieter", "turn down volume", "lower volume"]
        )
        
        self.register(
            "volume_set",
            SystemCommand(
                "volume_set",
                "osascript -e 'set volume output volume {level}'",
                "Set volume level",
                requires_param=True,
                param_name="level",
                success_message="Volume set to {level}%"
            ),
            aliases=["set volume to", "volume at", "set volume"]
        )
        
        self.register(
            "volume_max",
            SystemCommand(
                "volume_max",
                "osascript -e 'set volume output volume 100'",
                "Maximum volume",
                success_message="Volume set to maximum"
            ),
            aliases=["max volume", "maximum volume", "full volume"]
        )
        
        # =================================================================
        # Brightness Commands
        # =================================================================
        self.register(
            "brightness_up",
            SystemCommand(
                "brightness_up",
                "osascript -e 'tell application \"System Events\" to key code 144'",
                "Increase brightness",
                success_message="Brightness increased"
            ),
            aliases=["brightness up", "increase brightness", "brighter", "turn up brightness"]
        )
        
        self.register(
            "brightness_down",
            SystemCommand(
                "brightness_down",
                "osascript -e 'tell application \"System Events\" to key code 145'",
                "Decrease brightness",
                success_message="Brightness decreased"
            ),
            aliases=["brightness down", "decrease brightness", "dimmer", "turn down brightness", "dim screen"]
        )
        
        # =================================================================
        # Dark Mode Commands
        # =================================================================
        self.register(
            "dark_mode_on",
            SystemCommand(
                "dark_mode_on",
                "osascript -e 'tell app \"System Events\" to tell appearance preferences to set dark mode to true'",
                "Enable dark mode",
                success_message="Dark mode enabled"
            ),
            aliases=["dark mode on", "enable dark mode", "turn on dark mode", "switch to dark mode", "go dark"]
        )
        
        self.register(
            "dark_mode_off",
            SystemCommand(
                "dark_mode_off",
                "osascript -e 'tell app \"System Events\" to tell appearance preferences to set dark mode to false'",
                "Disable dark mode",
                success_message="Light mode enabled"
            ),
            aliases=["dark mode off", "disable dark mode", "turn off dark mode", "switch to light mode", "go light", "light mode"]
        )
        
        # =================================================================
        # Display Commands
        # =================================================================
        self.register(
            "lock_screen",
            SystemCommand(
                "lock_screen",
                "pmset displaysleepnow",
                "Lock screen",
                success_message="Screen locked"
            ),
            aliases=["lock screen", "lock", "lock computer", "lock mac", "sleep display"]
        )
        
        self.register(
            "screenshot",
            SystemCommand(
                "screenshot",
                "screencapture -x ~/Desktop/screenshot_$(date +%Y%m%d_%H%M%S).png",
                "Take screenshot",
                success_message="Screenshot saved to Desktop"
            ),
            aliases=["screenshot", "take screenshot", "capture screen", "screen capture", "take a screenshot"]
        )
        
        self.register(
            "screenshot_clipboard",
            SystemCommand(
                "screenshot_clipboard",
                "screencapture -c -x",
                "Screenshot to clipboard",
                success_message="Screenshot copied to clipboard"
            ),
            aliases=["screenshot to clipboard", "copy screenshot", "screenshot copy"]
        )
        
        # =================================================================
        # Do Not Disturb
        # =================================================================
        self.register(
            "dnd_on",
            SystemCommand(
                "dnd_on",
                "shortcuts run 'Set Focus' <<< 'Do Not Disturb' 2>/dev/null || osascript -e 'do shell script \"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean true\"'",
                "Enable Do Not Disturb",
                success_message="Do Not Disturb enabled"
            ),
            aliases=["do not disturb on", "dnd on", "turn on do not disturb", "enable dnd", "focus mode on"]
        )
        
        self.register(
            "dnd_off",
            SystemCommand(
                "dnd_off",
                "shortcuts run 'Set Focus' <<< 'Off' 2>/dev/null || osascript -e 'do shell script \"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean false\"'",
                "Disable Do Not Disturb",
                success_message="Do Not Disturb disabled"
            ),
            aliases=["do not disturb off", "dnd off", "turn off do not disturb", "disable dnd", "focus mode off"]
        )
        
        # =================================================================
        # Application Commands
        # =================================================================
        apps = {
            "safari": "Safari",
            "chrome": "Google Chrome",
            "firefox": "Firefox",
            "finder": "Finder",
            "terminal": "Terminal",
            "notes": "Notes",
            "calendar": "Calendar",
            "mail": "Mail",
            "messages": "Messages",
            "whatsapp": "WhatsApp",
            "telegram": "Telegram",
            "slack": "Slack",
            "discord": "Discord",
            "spotify": "Spotify",
            "music": "Music",
            "photos": "Photos",
            "settings": "System Preferences",
            "calculator": "Calculator",
            "preview": "Preview",
            "vscode": "Visual Studio Code",
            "xcode": "Xcode",
        }
        
        for alias, app_name in apps.items():
            # Open commands
            self.register(
                f"open_{alias}",
                AppCommand(f"open_{alias}", app_name, "open", f"Open {app_name}"),
                aliases=[
                    f"open {alias}",
                    f"launch {alias}",
                    f"start {alias}",
                    f"open {app_name.lower()}",
                ]
            )
            
            # Close commands
            self.register(
                f"close_{alias}",
                AppCommand(f"close_{alias}", app_name, "close", f"Close {app_name}"),
                aliases=[
                    f"close {alias}",
                    f"quit {alias}",
                    f"exit {alias}",
                    f"close {app_name.lower()}",
                ]
            )
        
        # =================================================================
        # Navigation Commands
        # =================================================================
        websites = {
            "google": "https://google.com",
            "youtube": "https://youtube.com",
            "github": "https://github.com",
            "twitter": "https://twitter.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "amazon": "https://amazon.com",
            "gmail": "https://mail.google.com",
        }
        
        for name, url in websites.items():
            self.register(
                f"goto_{name}",
                NavigationCommand(f"goto_{name}", url, f"Go to {name}"),
                aliases=[
                    f"go to {name}",
                    f"open {name}",
                    f"navigate to {name}",
                    f"visit {name}",
                    f"{name}.com",
                ]
            )
        
        # Generic URL navigation
        self.register(
            "open_url",
            NavigationCommand("open_url", None, "Open a URL"),
            aliases=["go to", "open url", "navigate to", "visit"]
        )
        
        # =================================================================
        # Media Controls
        # =================================================================
        self.register(
            "play_pause",
            SystemCommand(
                "play_pause",
                "osascript -e 'tell application \"System Events\" to key code 16 using command down'",
                "Play/Pause media",
                success_message="Toggled play/pause"
            ),
            aliases=["play", "pause", "play pause", "toggle play"]
        )
        
        self.register(
            "next_track",
            SystemCommand(
                "next_track",
                "osascript -e 'tell application \"System Events\" to key code 17 using command down'",
                "Next track",
                success_message="Skipped to next track"
            ),
            aliases=["next", "next track", "skip", "next song"]
        )
        
        self.register(
            "previous_track",
            SystemCommand(
                "previous_track",
                "osascript -e 'tell application \"System Events\" to key code 18 using command down'",
                "Previous track",
                success_message="Went to previous track"
            ),
            aliases=["previous", "previous track", "back", "previous song"]
        )
        
        logger.info(f"Registered {len(self.commands)} commands with {len(self.aliases)} aliases")
    
    def register(
        self,
        name: str,
        command: DirectCommand,
        aliases: Optional[List[str]] = None
    ):
        """
        Register a command with optional aliases.
        
        Args:
            name: Unique command identifier
            command: The command to register
            aliases: List of natural language phrases that trigger this command
        """
        self.commands[name] = command
        
        # Register aliases (normalized to lowercase)
        if aliases:
            for alias in aliases:
                self.aliases[alias.lower().strip()] = name
    
    def get_command(self, name: str) -> Optional[DirectCommand]:
        """Get command by name"""
        return self.commands.get(name)
    
    def match(self, user_input: str) -> Optional[tuple]:
        """
        Try to match user input to a direct command.
        
        Args:
            user_input: Natural language input from user
        
        Returns:
            Tuple of (command, extracted_params) or None if no match
        """
        normalized = user_input.lower().strip()
        
        # Try exact alias match first
        if normalized in self.aliases:
            cmd_name = self.aliases[normalized]
            return (self.commands[cmd_name], {})
        
        # Try to extract parameters (e.g., "set volume to 50")
        for alias, cmd_name in self.aliases.items():
            cmd = self.commands[cmd_name]
            
            if cmd.requires_param and alias in normalized:
                # Extract parameter value
                param = self._extract_param(normalized, alias, cmd.param_name)
                if param is not None:
                    return (cmd, {cmd.param_name: param})
        
        # Try prefix matching for commands
        for alias, cmd_name in self.aliases.items():
            if normalized.startswith(alias):
                remaining = normalized[len(alias):].strip()
                cmd = self.commands[cmd_name]
                
                if cmd.requires_param and remaining:
                    return (cmd, {cmd.param_name: remaining})
                elif not cmd.requires_param:
                    return (cmd, {})
        
        return None
    
    def _extract_param(
        self,
        user_input: str,
        alias: str,
        param_name: str
    ) -> Optional[Any]:
        """Extract parameter value from user input"""
        import re
        
        # Handle "set volume to 50" -> extract 50
        if param_name == "level":
            match = re.search(r'(\d+)\s*%?', user_input)
            if match:
                return int(match.group(1))
        
        # Handle "open url example.com" -> extract example.com
        if param_name == "url":
            # Remove the alias and get remaining
            remaining = user_input.replace(alias, "").strip()
            if remaining:
                return remaining
        
        return None
    
    def execute(
        self,
        user_input: str
    ) -> Optional[CommandResult]:
        """
        Try to match and execute a direct command.
        
        Args:
            user_input: Natural language input from user
        
        Returns:
            CommandResult if command matched and executed, None otherwise
        """
        match = self.match(user_input)
        if match:
            command, params = match
            logger.info(f"Executing direct command: {command.name} with params: {params}")
            return command.execute(params)
        return None
    
    def list_commands(self, category: Optional[CommandCategory] = None) -> List[str]:
        """List all registered commands, optionally filtered by category"""
        commands = []
        for name, cmd in self.commands.items():
            if category is None or cmd.category == category:
                commands.append(f"{name}: {cmd.description}")
        return commands
    
    def get_aliases(self, command_name: str) -> List[str]:
        """Get all aliases for a command"""
        return [alias for alias, name in self.aliases.items() if name == command_name]


# Global registry instance
command_registry = CommandRegistry()
