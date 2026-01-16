"""
System commands executor for macOS
"""
import subprocess
from typing import Dict, Any, Optional

from ..core.config import SYSTEM_COMMANDS, APP_ALIASES


class SystemExecutor:
    """Executes system-level commands on macOS"""
    
    def execute(self, command_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a system command.
        
        Args:
            command_name: Name of command (wifi_on, volume_up, etc.)
            params: Optional parameters for commands that need them
        
        Returns:
            Dict with success status and result/error
        """
        params = params or {}
        
        if command_name not in SYSTEM_COMMANDS:
            return {
                "success": False,
                "error": f"Unknown command: {command_name}"
            }
        
        command = SYSTEM_COMMANDS[command_name]
        
        # Replace parameters in command
        if params:
            for key, value in params.items():
                command = command.replace(f"{{{key}}}", str(value))
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip() if result.stdout else "Done",
                    "command": command_name
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() if result.stderr else "Command failed",
                    "command": command_name
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "command": command_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command_name
            }
    
    def open_app(self, app_name: str) -> Dict[str, Any]:
        """Open an application by name"""
        # Check aliases
        actual_name = APP_ALIASES.get(app_name.lower(), app_name)
        
        try:
            result = subprocess.run(
                ["open", "-a", actual_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": f"Opened {actual_name}",
                    "app": actual_name
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not open {actual_name}: {result.stderr}",
                    "app": actual_name
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app": app_name
            }
    
    def close_app(self, app_name: str) -> Dict[str, Any]:
        """Close an application by name"""
        actual_name = APP_ALIASES.get(app_name.lower(), app_name)
        
        script = f'quit app "{actual_name}"'
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "success": result.returncode == 0,
                "output": f"Closed {actual_name}" if result.returncode == 0 else result.stderr,
                "app": actual_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app": app_name
            }
    
    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in default browser"""
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        try:
            result = subprocess.run(
                ["open", url],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "success": result.returncode == 0,
                "output": f"Opened {url}" if result.returncode == 0 else result.stderr,
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def get_active_app(self) -> Optional[str]:
        """Get the currently active application"""
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        return frontApp
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
