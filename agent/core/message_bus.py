"""
Message Bus - Event-driven communication system for the agent

Provides centralized event handling for loose coupling between components.
"""
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import threading
import queue

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the agent system"""
    # Task lifecycle
    TASK_RECEIVED = "task_received"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # Planning events
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    PLAN_FAILED = "plan_failed"
    
    # Step execution
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRYING = "step_retrying"
    
    # Action execution
    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    
    # Vision events
    SCREENSHOT_TAKEN = "screenshot_taken"
    ELEMENT_FOUND = "element_found"
    ELEMENT_NOT_FOUND = "element_not_found"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    
    # User interaction
    CLARIFICATION_NEEDED = "clarification_needed"
    CLARIFICATION_RECEIVED = "clarification_received"
    USER_CONFIRMATION_NEEDED = "user_confirmation_needed"
    USER_CONFIRMATION_RECEIVED = "user_confirmation_received"
    
    # Voice events
    VOICE_LISTENING = "voice_listening"
    VOICE_RECOGNIZED = "voice_recognized"
    VOICE_SPEAKING = "voice_speaking"
    VOICE_DONE = "voice_done"
    
    # System events
    AGENT_READY = "agent_ready"
    AGENT_BUSY = "agent_busy"
    AGENT_IDLE = "agent_idle"
    AGENT_ERROR = "agent_error"
    
    # State changes
    STATE_CHANGED = "state_changed"
    CONTEXT_UPDATED = "context_updated"


@dataclass
class Event:
    """An event in the message bus"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""  # Component that generated the event
    
    def __repr__(self):
        return f"Event({self.type.value}, source={self.source})"


class EventHandler:
    """Wrapper for event handlers with metadata"""
    
    def __init__(
        self,
        callback: Callable[[Event], None],
        event_type: EventType,
        priority: int = 0,
        once: bool = False
    ):
        self.callback = callback
        self.event_type = event_type
        self.priority = priority
        self.once = once
        self.id = id(callback)
    
    def __call__(self, event: Event):
        self.callback(event)


class MessageBus:
    """
    Central event bus for agent component communication.
    
    Provides:
    - Publish/subscribe pattern for events
    - Synchronous and asynchronous event handling
    - Event history for debugging
    - Handler priority ordering
    
    Example:
        bus = MessageBus()
        
        def on_task_start(event):
            print(f"Task started: {event.data}")
        
        bus.subscribe(EventType.TASK_STARTED, on_task_start)
        bus.publish(EventType.TASK_STARTED, {"task": "open safari"})
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global message bus"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._max_history = 100
        self._lock = threading.Lock()
        self._async_queue = queue.Queue()
        self._running = False
        self._initialized = True
        
        logger.debug("MessageBus initialized")
    
    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        priority: int = 0,
        once: bool = False
    ) -> int:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            priority: Higher priority handlers called first (default 0)
            once: If True, handler is removed after first call
        
        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(callback, event_type, priority, once)
        
        with self._lock:
            self._handlers[event_type].append(handler)
            # Sort by priority (higher first)
            self._handlers[event_type].sort(key=lambda h: -h.priority)
        
        logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")
        return handler.id
    
    def unsubscribe(self, event_type: EventType, handler_id: int) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler_id: ID returned by subscribe()
        
        Returns:
            True if handler was found and removed
        """
        with self._lock:
            handlers = self._handlers[event_type]
            for i, handler in enumerate(handlers):
                if handler.id == handler_id:
                    handlers.pop(i)
                    logger.debug(f"Unsubscribed from {event_type.value}")
                    return True
        return False
    
    def publish(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: str = ""
    ) -> Event:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Optional event data
            source: Name of component publishing event
        
        Returns:
            The published event
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source
        )
        
        # Add to history
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        # Get handlers (copy to avoid modification during iteration)
        with self._lock:
            handlers = list(self._handlers[event_type])
        
        # Call handlers
        handlers_to_remove = []
        for handler in handlers:
            try:
                handler(event)
                if handler.once:
                    handlers_to_remove.append(handler.id)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
        
        # Remove one-time handlers
        for handler_id in handlers_to_remove:
            self.unsubscribe(event_type, handler_id)
        
        logger.debug(f"Published {event_type.value} to {len(handlers)} handlers")
        return event
    
    def publish_async(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: str = ""
    ):
        """
        Queue event for asynchronous processing.
        
        Args:
            event_type: Type of event
            data: Optional event data
            source: Name of component publishing event
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source
        )
        self._async_queue.put(event)
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 10
    ) -> List[Event]:
        """
        Get recent event history.
        
        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum events to return
        
        Returns:
            List of recent events
        """
        with self._lock:
            if event_type:
                filtered = [e for e in self._event_history if e.type == event_type]
            else:
                filtered = list(self._event_history)
            
            return filtered[-limit:]
    
    def clear_handlers(self, event_type: Optional[EventType] = None):
        """
        Clear event handlers.
        
        Args:
            event_type: Type to clear (None for all)
        """
        with self._lock:
            if event_type:
                self._handlers[event_type] = []
            else:
                self._handlers.clear()
    
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._event_history.clear()


# Global message bus instance
message_bus = MessageBus()


def subscribe(event_type: EventType):
    """
    Decorator for subscribing to events.
    
    Example:
        @subscribe(EventType.TASK_STARTED)
        def on_task_start(event):
            print(f"Task: {event.data}")
    """
    def decorator(func: Callable[[Event], None]):
        message_bus.subscribe(event_type, func)
        return func
    return decorator
