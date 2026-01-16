"""
Unit Tests for Message Bus
"""
import pytest
import time
from agent.core.message_bus import MessageBus, EventType, Event


class TestMessageBus:
    """Tests for MessageBus class"""
    
    def setup_method(self):
        """Reset message bus before each test"""
        self.bus = MessageBus()
        self.bus.clear_handlers()
        self.bus.clear_history()
    
    def test_singleton_pattern(self):
        """Test that MessageBus is a singleton"""
        bus1 = MessageBus()
        bus2 = MessageBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self):
        """Test basic subscribe and publish"""
        received = []
        
        def handler(event):
            received.append(event)
        
        self.bus.subscribe(EventType.TASK_RECEIVED, handler)
        self.bus.publish(EventType.TASK_RECEIVED, {"task": "test"}, "test_source")
        
        assert len(received) == 1
        assert received[0].type == EventType.TASK_RECEIVED
        assert received[0].data["task"] == "test"
    
    def test_multiple_handlers(self):
        """Test multiple handlers for same event"""
        results = []
        
        def handler1(event):
            results.append("h1")
        
        def handler2(event):
            results.append("h2")
        
        self.bus.subscribe(EventType.TASK_STARTED, handler1)
        self.bus.subscribe(EventType.TASK_STARTED, handler2)
        self.bus.publish(EventType.TASK_STARTED, {}, "test")
        
        assert len(results) == 2
        assert "h1" in results
        assert "h2" in results
    
    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        received = []
        
        def handler(event):
            received.append(event)
        
        handler_id = self.bus.subscribe(EventType.TASK_COMPLETED, handler)
        self.bus.publish(EventType.TASK_COMPLETED, {}, "test")
        assert len(received) == 1
        
        # Use unsubscribe with handler_id
        self.bus.unsubscribe(EventType.TASK_COMPLETED, handler_id)
        self.bus.publish(EventType.TASK_COMPLETED, {}, "test")
        assert len(received) == 1  # Still 1, handler removed
    
    def test_handler_priority(self):
        """Test handler priority ordering"""
        order = []
        
        def low_handler(event):
            order.append("low")
        
        def high_handler(event):
            order.append("high")
        
        self.bus.subscribe(EventType.STEP_STARTED, low_handler, priority=1)
        self.bus.subscribe(EventType.STEP_STARTED, high_handler, priority=10)
        self.bus.publish(EventType.STEP_STARTED, {}, "test")
        
        # Higher priority should run first
        assert order == ["high", "low"]
    
    def test_event_history(self):
        """Test event history is recorded"""
        self.bus.publish(EventType.TASK_RECEIVED, {"id": 1}, "test")
        self.bus.publish(EventType.TASK_STARTED, {"id": 1}, "test")
        
        history = self.bus.get_history(EventType.TASK_RECEIVED)
        assert len(history) >= 1
        
        all_history = self.bus.get_history()
        assert len(all_history) >= 2
    
    def test_event_data_types(self):
        """Test various data types in events"""
        received = []
        
        def handler(event):
            received.append(event.data)
        
        self.bus.subscribe(EventType.TASK_RECEIVED, handler)
        
        # Dict
        self.bus.publish(EventType.TASK_RECEIVED, {"key": "value"}, "test")
        # Nested
        self.bus.publish(EventType.TASK_RECEIVED, {"nested": {"a": 1}}, "test")
        # List
        self.bus.publish(EventType.TASK_RECEIVED, {"items": [1, 2, 3]}, "test")
        
        assert len(received) == 3
        assert received[0]["key"] == "value"
        assert received[1]["nested"]["a"] == 1
        assert received[2]["items"] == [1, 2, 3]
    
    def test_handler_exception_isolation(self):
        """Test that one handler exception doesn't affect others"""
        results = []
        
        def bad_handler(event):
            raise ValueError("Test error")
        
        def good_handler(event):
            results.append("success")
        
        self.bus.subscribe(EventType.TASK_FAILED, bad_handler)
        self.bus.subscribe(EventType.TASK_FAILED, good_handler)
        
        # Should not raise, and good_handler should still run
        self.bus.publish(EventType.TASK_FAILED, {}, "test")
        assert "success" in results


class TestEventType:
    """Tests for EventType enum"""
    
    def test_event_types_exist(self):
        """Test that expected event types exist"""
        expected = [
            "TASK_RECEIVED", "TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED",
            "STEP_STARTED", "STEP_COMPLETED", "STEP_FAILED",
            "ACTION_STARTED", "ACTION_COMPLETED", "ACTION_FAILED",
        ]
        
        for name in expected:
            assert hasattr(EventType, name)
    
    def test_event_type_values(self):
        """Test event type string values"""
        assert EventType.TASK_RECEIVED.value == "task_received"
        assert EventType.STEP_COMPLETED.value == "step_completed"


class TestEvent:
    """Tests for Event dataclass"""
    
    def test_event_creation(self):
        """Test Event creation"""
        event = Event(
            type=EventType.TASK_STARTED,
            data={"task": "test"},
            source="test_source"
        )
        
        assert event.type == EventType.TASK_STARTED
        assert event.data["task"] == "test"
        assert event.source == "test_source"
        # Event doesn't have id field, but has timestamp
        assert event.timestamp is not None
    
    def test_event_timestamps(self):
        """Test that events have timestamps"""
        import time
        e1 = Event(type=EventType.TASK_RECEIVED, data={}, source="test")
        time.sleep(0.01)
        e2 = Event(type=EventType.TASK_RECEIVED, data={}, source="test")
        
        # Both should have timestamps, e2 should be slightly later
        assert e1.timestamp is not None
        assert e2.timestamp is not None
        assert e2.timestamp >= e1.timestamp
