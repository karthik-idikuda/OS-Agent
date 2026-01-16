"""
Context Manager - Maintains conversation and execution context

This module manages the state and context for the AI agent, including:
- Conversation history
- Screen state tracking
- Element caching
- Session management
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from ..core.models import (
    ConversationMessage, MessageRole, ScreenAnalysis,
    ExecutionContext, Plan, Clarification
)

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages context for the AI agent.
    
    Maintains:
    - Conversation history with memory limits
    - Screen analysis results
    - Element position cache
    - Pending clarifications
    - Active task state
    """
    
    def __init__(self, max_history: int = 20):
        """
        Initialize context manager.
        
        Args:
            max_history: Maximum conversation messages to retain
        """
        self.max_history = max_history
        self.context = ExecutionContext()
        
        logger.debug("ContextManager initialized")
    
    # =========================================================================
    # Conversation Management
    # =========================================================================
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to conversation history"""
        self._add_message(MessageRole.USER, content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to conversation history"""
        self._add_message(MessageRole.ASSISTANT, content)
    
    def add_system_message(self, content: str) -> None:
        """Add a system message to conversation history"""
        self._add_message(MessageRole.SYSTEM, content)
    
    def _add_message(self, role: MessageRole, content: str) -> None:
        """Internal method to add message"""
        message = ConversationMessage(role=role, content=content)
        self.context.conversation_history.append(message)
        
        # Trim history if needed
        if len(self.context.conversation_history) > self.max_history:
            self.context.conversation_history = self.context.conversation_history[-self.max_history:]
    
    def get_conversation_history(self, n: Optional[int] = None) -> List[ConversationMessage]:
        """
        Get recent conversation history.
        
        Args:
            n: Number of messages to return (None for all)
        """
        if n is None:
            return list(self.context.conversation_history)
        return list(self.context.conversation_history[-n:])
    
    def get_conversation_text(self, n: int = 5) -> str:
        """Get recent conversation as formatted text"""
        messages = self.get_conversation_history(n)
        lines = []
        for msg in messages:
            role = msg.role.value.upper()
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)
    
    def clear_conversation(self) -> None:
        """Clear conversation history"""
        self.context.conversation_history.clear()
    
    # =========================================================================
    # Screen Context Management
    # =========================================================================
    
    def update_screen_analysis(self, analysis: ScreenAnalysis) -> None:
        """Update the current screen analysis"""
        self.context.last_screen_analysis = analysis
        self.context.last_screenshot = analysis.screenshot_path
    
    def get_screen_context(self) -> str:
        """
        Get current screen context as text.
        
        Returns description of what's on screen for LLM context.
        """
        if not self.context.last_screen_analysis:
            return "No screen context available"
        
        analysis = self.context.last_screen_analysis
        parts = [f"Active app: {analysis.active_app or 'Unknown'}"]
        
        if analysis.summary:
            parts.append(f"Screen: {analysis.summary}")
        
        if analysis.elements:
            element_texts = [e.text for e in analysis.elements[:5]]  # Top 5 elements
            parts.append(f"Visible elements: {', '.join(element_texts)}")
        
        return ". ".join(parts)
    
    def get_active_app(self) -> Optional[str]:
        """Get the currently active application"""
        if self.context.last_screen_analysis:
            return self.context.last_screen_analysis.active_app
        return None
    
    # =========================================================================
    # Element Cache Management
    # =========================================================================
    
    def cache_element(self, description: str, x: int, y: int) -> None:
        """
        Cache element position for quick lookup.
        
        Args:
            description: Element description (e.g., "search button")
            x, y: Screen coordinates
        """
        self.context.element_cache[description.lower()] = (x, y)
        self.context.last_found_element = {
            "description": description,
            "x": x,
            "y": y,
            "cached_at": datetime.now().isoformat()
        }
    
    def get_cached_element(self, description: str) -> Optional[Tuple[int, int]]:
        """
        Get cached element position.
        
        Args:
            description: Element description to look up
        
        Returns:
            Tuple of (x, y) or None if not cached
        """
        return self.context.element_cache.get(description.lower())
    
    def clear_element_cache(self) -> None:
        """Clear all cached element positions"""
        self.context.element_cache.clear()
        self.context.last_found_element = None
    
    def get_last_found_element(self) -> Optional[Dict[str, Any]]:
        """Get the last found element info"""
        return self.context.last_found_element
    
    # =========================================================================
    # Task State Management
    # =========================================================================
    
    def set_current_task(self, task: str, plan: Optional[Plan] = None) -> None:
        """
        Set the current task being executed.
        
        Args:
            task: Task description
            plan: Optional execution plan
        """
        self.context.current_task = task
        self.context.current_plan = plan
        self.context.current_step_index = 0
    
    def get_current_task(self) -> Optional[str]:
        """Get current task description"""
        return self.context.current_task
    
    def get_current_plan(self) -> Optional[Plan]:
        """Get current execution plan"""
        return self.context.current_plan
    
    def update_step_index(self, index: int) -> None:
        """Update current step index"""
        self.context.current_step_index = index
    
    def clear_current_task(self) -> None:
        """Clear current task state"""
        self.context.current_task = None
        self.context.current_plan = None
        self.context.current_step_index = 0
    
    # =========================================================================
    # Clarification Management
    # =========================================================================
    
    def add_clarification(self, clarification: Clarification) -> None:
        """Add a pending clarification"""
        self.context.pending_clarifications.append(clarification)
    
    def get_pending_clarifications(self) -> List[Clarification]:
        """Get all pending clarifications"""
        return [c for c in self.context.pending_clarifications if not c.answered]
    
    def answer_clarification(self, clarification_id: str, answer: str) -> bool:
        """
        Answer a pending clarification.
        
        Returns True if clarification was found and answered.
        """
        for c in self.context.pending_clarifications:
            if c.id == clarification_id:
                c.answered = True
                c.answer = answer
                c.answered_at = datetime.now()
                return True
        return False
    
    def clear_clarifications(self) -> None:
        """Clear all pending clarifications"""
        self.context.pending_clarifications.clear()
    
    # =========================================================================
    # Full Context for LLM
    # =========================================================================
    
    def get_full_context(self) -> str:
        """
        Get complete context for LLM prompting.
        
        Combines conversation, screen, and task context.
        """
        parts = []
        
        # Screen context
        screen_ctx = self.get_screen_context()
        if screen_ctx:
            parts.append(f"SCREEN: {screen_ctx}")
        
        # Current task
        if self.context.current_task:
            parts.append(f"CURRENT TASK: {self.context.current_task}")
            if self.context.current_plan:
                step = self.context.current_step_index
                total = len(self.context.current_plan.steps)
                parts.append(f"PROGRESS: Step {step + 1} of {total}")
        
        # Recent conversation
        recent = self.get_conversation_text(3)
        if recent:
            parts.append(f"RECENT CONVERSATION:\n{recent}")
        
        # Pending clarifications
        pending = self.get_pending_clarifications()
        if pending:
            questions = [c.question for c in pending]
            parts.append(f"AWAITING ANSWERS: {', '.join(questions)}")
        
        return "\n\n".join(parts)
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def reset(self) -> None:
        """Reset all context to initial state"""
        self.context = ExecutionContext()
        logger.debug("Context reset to initial state")
    
    def get_session_id(self) -> str:
        """Get current session ID"""
        return self.context.session_id
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (datetime.now() - self.context.started_at).total_seconds()


# Global instance
context_manager = ContextManager()
