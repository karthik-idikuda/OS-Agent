"""
Task Planner - Breaks down user requests into executable steps
"""
import json
from typing import Optional, List, Dict, Any

from ..core.config import config, SYSTEM_COMMANDS, APP_ALIASES
from ..core.models import Plan, Step, Action, ActionType, TaskStatus
from .llm_client import LLMClient


PLANNER_SYSTEM_PROMPT = """You are a macOS desktop automation assistant. Your job is to break down user requests into executable steps.

AVAILABLE ACTIONS:
1. SYSTEM_COMMAND - Direct system commands:
   - wifi_on, wifi_off: Control WiFi
   - bluetooth_on, bluetooth_off: Control Bluetooth
   - volume_up, volume_down, volume_mute, volume_unmute: Audio control
   - brightness_up, brightness_down: Display brightness
   - lock_screen, sleep: System power
   
2. OPEN_APP - Open an application by name
3. CLOSE_APP - Close an application
4. OPEN_URL - Open a URL in the default browser
5. CLICK - Click at a location (requires finding element first)
6. TYPE - Type text (into focused field)
7. PRESS_KEY - Press a key (enter, tab, escape, etc.)
8. HOTKEY - Press key combination (cmd+c, cmd+v, etc.)
9. SCROLL - Scroll up/down
10. WAIT - Wait for seconds
11. FIND_ELEMENT - Use vision to find element on screen
12. VERIFY - Verify expected state
13. ASK_USER - Ask user for clarification

RULES:
1. For simple commands (wifi, volume, etc.) → Use SYSTEM_COMMAND directly
2. For app operations → OPEN_APP first, then interact
3. For clicking buttons/links → FIND_ELEMENT first, then CLICK
4. Always include VERIFY steps after important actions
5. If anything is unclear, use ASK_USER to get clarification
6. Keep plans short and practical (max 10 steps)
7. Include wait times where needed (apps need time to load)

OUTPUT FORMAT (JSON only):
{
    "understood": true/false,
    "clarifications_needed": ["question1", "question2"],  // If anything unclear
    "plan": {
        "goal": "what we're trying to achieve",
        "steps": [
            {
                "id": 1,
                "action": "ACTION_TYPE",
                "params": {"key": "value"},
                "reasoning": "why this step",
                "expected_outcome": "what should happen",
                "requires_confirmation": false
            }
        ]
    },
    "suggestions": ["helpful tip 1"]  // Optional suggestions for user
}

EXAMPLES:
- "turn on wifi" → SYSTEM_COMMAND wifi_on (1 step)
- "open youtube and search for music" → OPEN_URL youtube.com, WAIT, FIND_ELEMENT search, CLICK, TYPE music, PRESS_KEY enter (6 steps)
- "send message to John on WhatsApp" → ASK_USER "What message?" (need clarification)
"""


class TaskPlanner:
    """Plans executable steps from user requests"""
    
    def __init__(self):
        self.llm = LLMClient()
    
    def create_plan(self, user_request: str, context: Optional[Dict] = None) -> Plan:
        """
        Create execution plan from user request.
        
        Args:
            user_request: Natural language request
            context: Optional context (screen state, conversation history)
        
        Returns:
            Plan with steps to execute
        """
        # Build context string
        context_str = ""
        if context:
            if context.get("screen_summary"):
                context_str += f"\nCurrent screen: {context['screen_summary']}"
            if context.get("active_app"):
                context_str += f"\nActive app: {context['active_app']}"
        
        prompt = f"""User request: "{user_request}"
{context_str}

Create an execution plan. Remember:
- Simple system commands (wifi, volume) should be direct SYSTEM_COMMAND actions
- App operations need OPEN_APP first
- Ask for clarification if the request is ambiguous
- Be efficient, minimize steps

JSON only:"""
        
        response = self.llm.generate(prompt, system_prompt=PLANNER_SYSTEM_PROMPT, json_mode=True)
        
        return self._parse_plan_response(user_request, response)
    
    def replan(self, original_goal: str, failed_step: Step, error: str,
               context: Optional[Dict] = None) -> Plan:
        """
        Create new plan after a step failed.
        
        Args:
            original_goal: Original user request
            failed_step: The step that failed
            error: Error message
            context: Current context
        
        Returns:
            New plan attempting to recover
        """
        context_str = ""
        if context:
            if context.get("screen_summary"):
                context_str += f"\nCurrent screen: {context['screen_summary']}"
        
        prompt = f"""Original goal: "{original_goal}"

PREVIOUS STEP FAILED:
- Step: {failed_step.action.type.value} - {failed_step.action.description}
- Error: {error}
{context_str}

Create a recovery plan. Consider:
1. Alternative approaches
2. Whether to ask user for help
3. Whether the goal is still achievable

JSON only:"""
        
        response = self.llm.generate(prompt, system_prompt=PLANNER_SYSTEM_PROMPT, json_mode=True)
        
        return self._parse_plan_response(original_goal, response)
    
    def should_ask_clarification(self, user_request: str) -> Optional[List[str]]:
        """
        Check if request needs clarification before planning.
        
        Returns:
            List of questions to ask, or None if clear
        """
        # Quick check for ambiguous requests
        ambiguous_patterns = [
            ("send", "message", "to"),      # Who? What message?
            ("search", "for"),               # Where to search?
            ("open", "and", "do"),           # Vague action
        ]
        
        request_lower = user_request.lower()
        
        # Use LLM for complex cases
        prompt = f"""User request: "{user_request}"

Is this request clear enough to execute? Consider:
1. Is there missing information? (who, what, where)
2. Are there multiple interpretations?

Return JSON:
{{"needs_clarification": true/false, "questions": ["question1", "question2"]}}

JSON only:"""
        
        try:
            response = self.llm.generate(prompt, json_mode=True)
            data = self._parse_json(response)
            
            if data.get("needs_clarification"):
                return data.get("questions", ["Can you provide more details?"])
            return None
        except:
            return None
    
    def _parse_plan_response(self, goal: str, response: str) -> Plan:
        """Parse LLM response into Plan object"""
        try:
            data = self._parse_json(response)
            
            # Check if clarification needed
            if not data.get("understood", True) or data.get("clarifications_needed"):
                return Plan(
                    goal=goal,
                    steps=[],
                    clarifications_needed=data.get("clarifications_needed", ["Please provide more details"]),
                    status=TaskStatus.WAITING_USER
                )
            
            # Parse steps
            steps = []
            plan_data = data.get("plan", {})
            
            for step_data in plan_data.get("steps", []):
                action_type = self._parse_action_type(step_data.get("action", ""))
                
                action = Action(
                    type=action_type,
                    description=step_data.get("reasoning", ""),
                    params=step_data.get("params", {})
                )
                
                step = Step(
                    id=step_data.get("id", len(steps) + 1),
                    action=action,
                    reasoning=step_data.get("reasoning", ""),
                    expected_outcome=step_data.get("expected_outcome", ""),
                    requires_confirmation=step_data.get("requires_confirmation", False)
                )
                steps.append(step)
            
            return Plan(
                goal=plan_data.get("goal", goal),
                steps=steps,
                suggestions=data.get("suggestions", []),
                status=TaskStatus.PENDING
            )
            
        except Exception as e:
            # Return error plan
            return Plan(
                goal=goal,
                steps=[
                    Step(
                        id=1,
                        action=Action(type=ActionType.ERROR, description=f"Planning failed: {e}"),
                        reasoning="Could not parse plan",
                        expected_outcome="None"
                    )
                ],
                status=TaskStatus.FAILED
            )
    
    def _parse_action_type(self, action_str: str) -> ActionType:
        """Convert string to ActionType enum"""
        action_map = {
            "SYSTEM_COMMAND": ActionType.SYSTEM_COMMAND,
            "OPEN_APP": ActionType.OPEN_APP,
            "CLOSE_APP": ActionType.CLOSE_APP,
            "OPEN_URL": ActionType.OPEN_URL,
            "CLICK": ActionType.CLICK,
            "DOUBLE_CLICK": ActionType.DOUBLE_CLICK,
            "RIGHT_CLICK": ActionType.RIGHT_CLICK,
            "TYPE": ActionType.TYPE,
            "PRESS_KEY": ActionType.PRESS_KEY,
            "HOTKEY": ActionType.HOTKEY,
            "SCROLL": ActionType.SCROLL,
            "WAIT": ActionType.WAIT,
            "FIND_ELEMENT": ActionType.FIND_ELEMENT,
            "VERIFY": ActionType.VERIFY,
            "ASK_USER": ActionType.ASK_USER,
            "DONE": ActionType.DONE,
        }
        return action_map.get(action_str.upper(), ActionType.ERROR)
    
    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from LLM response"""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)
