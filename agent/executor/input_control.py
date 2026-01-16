"""
Input control for mouse and keyboard automation
"""
import time
from typing import Dict, Any, Optional, Tuple, List

import pyautogui

from ..core.config import config

# Disable PyAutoGUI fail-safe (moving to corner stops script)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1


class InputController:
    """Controls mouse and keyboard input"""
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
    
    # ========== MOUSE ACTIONS ==========
    
    def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """
        Click at coordinates.
        
        Args:
            x, y: Screen coordinates
            button: "left", "right", or "middle"
        """
        try:
            # Validate coordinates
            if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
                return {
                    "success": False,
                    "error": f"Coordinates ({x}, {y}) out of screen bounds"
                }
            
            pyautogui.click(x, y, button=button)
            time.sleep(config.executor.click_delay)
            
            return {
                "success": True,
                "output": f"Clicked at ({x}, {y})",
                "position": (x, y)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        """Double click at coordinates"""
        try:
            pyautogui.doubleClick(x, y)
            time.sleep(config.executor.click_delay)
            
            return {
                "success": True,
                "output": f"Double-clicked at ({x}, {y})",
                "position": (x, y)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def right_click(self, x: int, y: int) -> Dict[str, Any]:
        """Right click at coordinates"""
        return self.click(x, y, button="right")
    
    def move_to(self, x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
        """Move mouse to coordinates"""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {
                "success": True,
                "output": f"Moved to ({x}, {y})",
                "position": (x, y)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def drag(self, start: Tuple[int, int], end: Tuple[int, int], 
             duration: float = 0.5) -> Dict[str, Any]:
        """Drag from start to end coordinates"""
        try:
            pyautogui.moveTo(start[0], start[1])
            pyautogui.drag(
                end[0] - start[0], 
                end[1] - start[1], 
                duration=duration
            )
            return {
                "success": True,
                "output": f"Dragged from {start} to {end}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def scroll(self, amount: int, x: Optional[int] = None, 
               y: Optional[int] = None) -> Dict[str, Any]:
        """
        Scroll at current or specified position.
        
        Args:
            amount: Positive = up, Negative = down
            x, y: Optional position to scroll at
        """
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            
            pyautogui.scroll(amount)
            
            direction = "up" if amount > 0 else "down"
            return {
                "success": True,
                "output": f"Scrolled {direction} ({abs(amount)} units)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return pyautogui.position()
    
    # ========== KEYBOARD ACTIONS ==========
    
    def type_text(self, text: str, interval: Optional[float] = None) -> Dict[str, Any]:
        """
        Type text string.
        
        Args:
            text: Text to type
            interval: Time between keystrokes
        """
        try:
            interval = interval or config.executor.type_interval
            pyautogui.typewrite(text, interval=interval)
            
            return {
                "success": True,
                "output": f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def type_unicode(self, text: str) -> Dict[str, Any]:
        """Type text with unicode support (slower but handles special chars)"""
        try:
            # Use pyperclip + paste for unicode
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("command", "v")
            
            return {
                "success": True,
                "output": f"Typed (unicode): {text[:50]}{'...' if len(text) > 50 else ''}"
            }
        except ImportError:
            # Fallback: use AppleScript
            import subprocess
            escaped = text.replace('"', '\\"')
            subprocess.run([
                "osascript", "-e",
                f'tell application "System Events" to keystroke "{escaped}"'
            ])
            return {
                "success": True,
                "output": f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """
        Press a single key.
        
        Args:
            key: Key name (enter, tab, escape, space, backspace, delete, 
                 up, down, left, right, etc.)
        """
        try:
            # Map common key names
            key_map = {
                "enter": "return",
                "return": "return",
                "esc": "escape",
                "del": "delete",
                "ctrl": "control",
                "cmd": "command",
                "opt": "option",
                "alt": "option",
            }
            key = key_map.get(key.lower(), key.lower())
            
            pyautogui.press(key)
            
            return {
                "success": True,
                "output": f"Pressed: {key}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def hotkey(self, *keys: str) -> Dict[str, Any]:
        """
        Press key combination.
        
        Args:
            keys: Keys to press together (e.g., "command", "c" for Cmd+C)
        """
        try:
            # Map key names
            key_map = {
                "cmd": "command",
                "ctrl": "control",
                "opt": "option",
                "alt": "option",
            }
            mapped_keys = [key_map.get(k.lower(), k.lower()) for k in keys]
            
            pyautogui.hotkey(*mapped_keys)
            
            return {
                "success": True,
                "output": f"Pressed: {'+'.join(keys)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== UTILITY ==========
    
    def wait(self, seconds: float) -> Dict[str, Any]:
        """Wait for specified time"""
        try:
            time.sleep(seconds)
            return {
                "success": True,
                "output": f"Waited {seconds} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
