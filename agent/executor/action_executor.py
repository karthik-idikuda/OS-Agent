"""
Action Executor - Executes individual actions
"""
from typing import Dict, Any, Optional

from ..core.models import Action, ActionType
from .system import SystemExecutor
from .input_control import InputController


class ActionExecutor:
    """
    Executes actions from the planner.
    Combines system commands and input control.
    """
    
    def __init__(self):
        self.system = SystemExecutor()
        self.input = InputController()
        
        # Last found element coordinates (for click after find)
        self.last_found_element = None
    
    def execute(self, action: Action, vision_analyzer=None) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action to execute
            vision_analyzer: Optional vision module for FIND_ELEMENT actions
        
        Returns:
            Dict with success status and result
        """
        action_type = action.type
        params = action.params
        
        try:
            # System commands
            if action_type == ActionType.SYSTEM_COMMAND:
                cmd = params.get("command", "")
                cmd_params = params.get("params", {})
                return self.system.execute(cmd, cmd_params)
            
            # App control
            elif action_type == ActionType.OPEN_APP:
                app = params.get("app", "")
                return self.system.open_app(app)
            
            elif action_type == ActionType.CLOSE_APP:
                app = params.get("app", "")
                return self.system.close_app(app)
            
            elif action_type == ActionType.OPEN_URL:
                url = params.get("url", "")
                return self.system.open_url(url)
            
            # Mouse actions
            elif action_type == ActionType.CLICK:
                x = params.get("x", 0)
                y = params.get("y", 0)
                
                # Use last found element if coordinates not provided
                if x == 0 and y == 0 and self.last_found_element:
                    x = self.last_found_element.get("x", 0)
                    y = self.last_found_element.get("y", 0)
                
                if x == 0 and y == 0:
                    return {
                        "success": False,
                        "error": "No coordinates provided. Use FIND_ELEMENT first."
                    }
                
                return self.input.click(x, y)
            
            elif action_type == ActionType.DOUBLE_CLICK:
                x = params.get("x", self.last_found_element.get("x", 0) if self.last_found_element else 0)
                y = params.get("y", self.last_found_element.get("y", 0) if self.last_found_element else 0)
                return self.input.double_click(x, y)
            
            elif action_type == ActionType.RIGHT_CLICK:
                x = params.get("x", self.last_found_element.get("x", 0) if self.last_found_element else 0)
                y = params.get("y", self.last_found_element.get("y", 0) if self.last_found_element else 0)
                return self.input.right_click(x, y)
            
            elif action_type == ActionType.MOVE_TO:
                x = params.get("x", 0)
                y = params.get("y", 0)
                return self.input.move_to(x, y)
            
            elif action_type == ActionType.SCROLL:
                amount = params.get("amount", -3)  # Negative = down
                return self.input.scroll(amount)
            
            elif action_type == ActionType.DRAG:
                start = params.get("start", (0, 0))
                end = params.get("end", (0, 0))
                return self.input.drag(start, end)
            
            # Keyboard actions
            elif action_type == ActionType.TYPE:
                text = params.get("text", "")
                # Use unicode typing for better compatibility
                return self.input.type_unicode(text)
            
            elif action_type == ActionType.PRESS_KEY:
                key = params.get("key", "")
                return self.input.press_key(key)
            
            elif action_type == ActionType.HOTKEY:
                keys = params.get("keys", [])
                return self.input.hotkey(*keys)
            
            # Vision actions (require vision_analyzer)
            elif action_type == ActionType.FIND_ELEMENT:
                if not vision_analyzer:
                    return {
                        "success": False,
                        "error": "Vision analyzer not available"
                    }
                
                target = params.get("target", "")
                result = vision_analyzer.find_element(target)
                
                if result.get("found"):
                    self.last_found_element = result
                    return {
                        "success": True,
                        "output": f"Found '{target}' at ({result['x']}, {result['y']})",
                        "element": result
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Could not find '{target}' on screen"
                    }
            
            elif action_type == ActionType.VERIFY:
                if not vision_analyzer:
                    return {
                        "success": False,
                        "error": "Vision analyzer not available"
                    }
                
                expected = params.get("expected", "")
                result = vision_analyzer.verify_action(expected)
                
                return {
                    "success": result.get("verified", False),
                    "output": result.get("reason", ""),
                    "verification": result
                }
            
            # Utility actions
            elif action_type == ActionType.WAIT:
                seconds = params.get("seconds", 1)
                return self.input.wait(seconds)
            
            elif action_type == ActionType.SCREENSHOT:
                if vision_analyzer:
                    result = vision_analyzer.screen_capture.capture()
                    return {
                        "success": True,
                        "output": f"Screenshot saved: {result['filepath']}",
                        "screenshot": result
                    }
                return {
                    "success": False,
                    "error": "Screenshot capture not available"
                }
            
            elif action_type == ActionType.ASK_USER:
                # This should be handled by orchestrator
                question = params.get("question", "Need more information")
                return {
                    "success": True,
                    "needs_input": True,
                    "question": question
                }
            
            elif action_type == ActionType.DONE:
                return {
                    "success": True,
                    "output": "Task completed"
                }
            
            elif action_type == ActionType.ERROR:
                return {
                    "success": False,
                    "error": params.get("message", "Unknown error")
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
