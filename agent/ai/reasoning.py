"""
Reasoning Engine - Chain-of-thought reasoning for complex tasks

This module provides advanced reasoning capabilities using Llama for:
- Intent classification
- Task decomposition
- Clarification generation
- Suggestion and alternative generation
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.models import (
    TaskIntent, IntentType, Confidence, Clarification, Suggestion,
    ActionType, Action
)
from ..planner.llm_client import LLMClient
from ..commands.command_registry import command_registry

logger = logging.getLogger(__name__)


INTENT_PROMPT = """You are an AI assistant that classifies user intents for a macOS automation agent.

Classify the user's request into one of these categories:
- SYSTEM_CONTROL: WiFi, Bluetooth, Volume, Brightness, Dark mode, Lock screen, Screenshot
- APP_LAUNCH: Opening an application
- APP_CLOSE: Closing an application
- NAVIGATION: Going to a URL or opening a file
- MULTI_STEP_TASK: Complex tasks requiring multiple steps (e.g., "send message to John on WhatsApp")
- SEARCH_TASK: Searching for something (e.g., "search for Python tutorials on YouTube")
- COMMUNICATION: Sending messages, emails
- QUESTION: User asking a question
- CLARIFICATION: User providing additional information
- CONFIRMATION: Yes/No response
- CANCELLATION: User wants to cancel

For the request, return JSON only:
{{
    "intent": "INTENT_TYPE",
    "confidence": 0.0-1.0,
    "is_direct_command": true/false,
    "target_app": "app name if applicable",
    "target_url": "URL if applicable",
    "action_verb": "main action verb",
    "subtasks": ["list of steps if complex task"],
    "needs_clarification": true/false,
    "clarification_question": "question if needed"
}}

User request: "{user_input}"
Current app: {current_app}

JSON only:"""


DECOMPOSITION_PROMPT = """You are an AI that breaks down complex tasks into executable steps for a macOS automation agent.

The agent can perform these actions:
- CLICK: Click at coordinates or on an element
- TYPE: Type text
- PRESS_KEY: Press keyboard keys (enter, escape, tab, etc.)
- HOTKEY: Keyboard shortcuts (cmd+c, cmd+v, etc.)
- OPEN_APP: Open an application
- CLOSE_APP: Close an application
- OPEN_URL: Open a URL
- SCROLL: Scroll up or down
- WAIT: Wait for a duration
- FIND_ELEMENT: Find a UI element (button, text field, etc.)
- VERIFY: Verify a condition on screen

For the task, create a step-by-step plan. Return JSON only:
{{
    "goal": "What we're trying to accomplish",
    "subtasks": [
        {{
            "step": 1,
            "description": "What this step does",
            "action": "ACTION_TYPE",
            "params": {{}},
            "verify": "What to verify after this step"
        }}
    ],
    "estimated_time_sec": 10,
    "needs_clarification": false,
    "clarification_questions": []
}}

Task: "{task}"
Current screen context: {context}

JSON only:"""


CLARIFICATION_PROMPT = """You are an AI assistant helping a user with macOS automation.

The user said: "{user_input}"

Based on this request, identify what information is missing or unclear.
Consider:
- Is a target specified? (which contact, which file, which app)
- Are specific parameters needed? (volume level, message content)
- Is there ambiguity? (multiple possible interpretations)

Return JSON only:
{{
    "needs_clarification": true/false,
    "missing_info": ["list of missing pieces"],
    "questions": [
        {{
            "question": "The question to ask",
            "context": "Why we need this info",
            "options": ["suggested answers if applicable"]
        }}
    ]
}}

JSON only:"""


SUGGESTION_PROMPT = """You are an AI assistant for a macOS automation agent.

The user's task failed: "{task}"
Error: "{error}"
Failed step: "{failed_step}"

Suggest alternatives or recovery actions. Consider:
- Different approaches to achieve the same goal
- Simpler alternatives
- Related actions the user might want

Return JSON only:
{{
    "suggestions": [
        {{
            "text": "Suggestion description",
            "confidence": "high/medium/low",
            "action_type": "ACTION_TYPE if applicable"
        }}
    ],
    "can_retry": true/false,
    "alternative_approach": "Different way to achieve the goal"
}}

JSON only:"""


class ReasoningEngine:
    """
    Advanced reasoning engine for task understanding and planning.
    
    Uses LLM for:
    - Classifying user intents
    - Decomposing complex tasks
    - Generating clarification questions
    - Suggesting alternatives when tasks fail
    
    Works without LLM by falling back to direct command matching only.
    """
    
    def __init__(self):
        from ..core.config import config
        self._llm_enabled = config.ollama.is_enabled
        self.llm = LLMClient() if self._llm_enabled else None
    
    @property
    def is_llm_available(self) -> bool:
        """Check if LLM reasoning is available"""
        return self._llm_enabled and self.llm is not None
    
    def analyze_intent(
        self,
        user_input: str,
        current_app: Optional[str] = None
    ) -> TaskIntent:
        """
        Analyze user input to determine intent.
        
        First checks against direct command registry, then uses LLM for
        more complex understanding (if available).
        
        Args:
            user_input: The user's natural language request
            current_app: Name of currently focused app (for context)
        
        Returns:
            TaskIntent with classification and extracted information
        """
        # First, try direct command matching (fast path - always works)
        direct_match = command_registry.match(user_input)
        if direct_match:
            command, params = direct_match
            return TaskIntent(
                type=IntentType.SYSTEM_CONTROL if command.category.value == "system" 
                     else IntentType.APP_LAUNCH if "open" in command.name
                     else IntentType.APP_CLOSE if "close" in command.name
                     else IntentType.NAVIGATION,
                raw_input=user_input,
                confidence=1.0,
                matched_command=command.name,
                is_direct_command=True,
                parameters=params
            )
        
        # If no LLM configured, return unknown intent
        if not self.is_llm_available:
            return TaskIntent(
                type=IntentType.UNKNOWN,
                raw_input=user_input,
                confidence=0.0,
                is_direct_command=False
            )
        
        # Use LLM for complex intent classification
        try:
            prompt = INTENT_PROMPT.format(
                user_input=user_input,
                current_app=current_app or "Unknown"
            )
            
            response = self.llm.generate(prompt)
            data = self._parse_json(response)
            
            intent_type = self._map_intent_type(data.get("intent", "UNKNOWN"))
            
            return TaskIntent(
                type=intent_type,
                raw_input=user_input,
                confidence=data.get("confidence", 0.5),
                target_app=data.get("target_app"),
                target_url=data.get("target_url"),
                action_verb=data.get("action_verb"),
                is_direct_command=data.get("is_direct_command", False),
                subtasks=data.get("subtasks", [])
            )
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return TaskIntent(
                type=IntentType.UNKNOWN,
                raw_input=user_input,
                confidence=0.0
            )
    
    def decompose_task(
        self,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Break down a complex task into executable steps.
        
        Args:
            task: The user's task description
            context: Current screen context
        
        Returns:
            Dict with goal, subtasks, and metadata
        """
        try:
            prompt = DECOMPOSITION_PROMPT.format(
                task=task,
                context=context or "No specific context"
            )
            
            response = self.llm.generate(prompt)
            data = self._parse_json(response)
            
            # Validate and transform subtasks
            subtasks = []
            for step in data.get("subtasks", []):
                action_type = self._map_action_type(step.get("action", "WAIT"))
                subtasks.append({
                    "step": step.get("step", len(subtasks) + 1),
                    "description": step.get("description", ""),
                    "action_type": action_type,
                    "params": step.get("params", {}),
                    "verify": step.get("verify")
                })
            
            return {
                "goal": data.get("goal", task),
                "subtasks": subtasks,
                "estimated_time_sec": data.get("estimated_time_sec", 30),
                "needs_clarification": data.get("needs_clarification", False),
                "clarification_questions": data.get("clarification_questions", [])
            }
            
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return {
                "goal": task,
                "subtasks": [],
                "error": str(e)
            }
    
    def generate_clarifications(
        self,
        user_input: str
    ) -> List[Clarification]:
        """
        Generate clarification questions for ambiguous requests.
        
        Args:
            user_input: The user's request
        
        Returns:
            List of Clarification objects with questions to ask
        """
        try:
            prompt = CLARIFICATION_PROMPT.format(user_input=user_input)
            response = self.llm.generate(prompt)
            data = self._parse_json(response)
            
            if not data.get("needs_clarification", False):
                return []
            
            clarifications = []
            for q in data.get("questions", []):
                clarifications.append(Clarification(
                    question=q.get("question", ""),
                    context=q.get("context", ""),
                    options=q.get("options", [])
                ))
            
            return clarifications
            
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return []
    
    def suggest_alternatives(
        self,
        task: str,
        error: str,
        failed_step: Optional[str] = None
    ) -> List[Suggestion]:
        """
        Generate alternative suggestions when a task fails.
        
        Args:
            task: The original task that failed
            error: Error message
            failed_step: Description of the step that failed
        
        Returns:
            List of Suggestion objects with alternatives
        """
        try:
            prompt = SUGGESTION_PROMPT.format(
                task=task,
                error=error,
                failed_step=failed_step or "Unknown step"
            )
            response = self.llm.generate(prompt)
            data = self._parse_json(response)
            
            suggestions = []
            for s in data.get("suggestions", []):
                confidence = Confidence.HIGH if s.get("confidence") == "high" \
                    else Confidence.LOW if s.get("confidence") == "low" \
                    else Confidence.MEDIUM
                
                suggestions.append(Suggestion(
                    text=s.get("text", ""),
                    confidence=confidence,
                    alternatives=[data.get("alternative_approach")] if data.get("alternative_approach") else []
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return []
    
    def is_confirmation(self, user_input: str) -> Tuple[bool, bool]:
        """
        Check if user input is a confirmation (yes/no).
        
        Returns:
            Tuple of (is_confirmation, is_affirmative)
        """
        input_lower = user_input.lower().strip()
        
        affirmative = ["yes", "y", "yeah", "yep", "sure", "ok", "okay", "do it", 
                       "go ahead", "proceed", "confirm", "approved", "correct"]
        negative = ["no", "n", "nope", "nah", "cancel", "stop", "abort", 
                    "don't", "nevermind", "never mind"]
        
        for word in affirmative:
            if word in input_lower:
                return (True, True)
        
        for word in negative:
            if word in input_lower:
                return (True, False)
        
        return (False, False)
    
    def is_cancellation(self, user_input: str) -> bool:
        """Check if user wants to cancel current task"""
        cancel_words = ["cancel", "stop", "abort", "quit", "exit", "nevermind", 
                        "never mind", "forget it", "don't do it"]
        input_lower = user_input.lower()
        return any(word in input_lower for word in cancel_words)
    
    def _map_intent_type(self, intent_str: str) -> IntentType:
        """Map string intent to IntentType enum"""
        mapping = {
            "SYSTEM_CONTROL": IntentType.SYSTEM_CONTROL,
            "APP_LAUNCH": IntentType.APP_LAUNCH,
            "APP_CLOSE": IntentType.APP_CLOSE,
            "NAVIGATION": IntentType.NAVIGATION,
            "MULTI_STEP_TASK": IntentType.MULTI_STEP_TASK,
            "SEARCH_TASK": IntentType.SEARCH_TASK,
            "COMMUNICATION": IntentType.COMMUNICATION,
            "QUESTION": IntentType.QUESTION,
            "CLARIFICATION": IntentType.CLARIFICATION,
            "CONFIRMATION": IntentType.CONFIRMATION,
            "CANCELLATION": IntentType.CANCELLATION,
        }
        return mapping.get(intent_str.upper(), IntentType.UNKNOWN)
    
    def _map_action_type(self, action_str: str) -> ActionType:
        """Map string action to ActionType enum"""
        mapping = {
            "CLICK": ActionType.CLICK,
            "DOUBLE_CLICK": ActionType.DOUBLE_CLICK,
            "TYPE": ActionType.TYPE,
            "PRESS_KEY": ActionType.PRESS_KEY,
            "HOTKEY": ActionType.HOTKEY,
            "OPEN_APP": ActionType.OPEN_APP,
            "CLOSE_APP": ActionType.CLOSE_APP,
            "OPEN_URL": ActionType.OPEN_URL,
            "SCROLL": ActionType.SCROLL,
            "WAIT": ActionType.WAIT,
            "FIND_ELEMENT": ActionType.FIND_ELEMENT,
            "VERIFY": ActionType.VERIFY,
        }
        return mapping.get(action_str.upper(), ActionType.WAIT)
    
    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from LLM response"""
        text = text.strip()
        # Remove markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)


# Global instance
reasoning_engine = ReasoningEngine()
