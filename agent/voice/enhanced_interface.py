"""
Enhanced Voice Interface - Advanced speech recognition and TTS

Improvements over original:
- Multiple TTS voice options (male/female, different accents)
- Improved speech recognition with noise filtering
- Customizable wake words
- Voice feedback for all agent states
- Integration with message bus for state events
"""
import asyncio
import logging
import threading
import queue
import time
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.message_bus import message_bus, EventType

logger = logging.getLogger(__name__)


class TTSVoice(Enum):
    """Available TTS voices (Edge TTS)"""
    # US English
    ARIA = "en-US-AriaNeural"        # Female, professional
    JENNY = "en-US-JennyNeural"      # Female, friendly
    GUY = "en-US-GuyNeural"          # Male, professional
    DAVIS = "en-US-DavisNeural"      # Male, casual
    # UK English
    SONIA = "en-GB-SoniaNeural"      # Female, British
    RYAN = "en-GB-RyanNeural"        # Male, British
    # Australian English
    NATASHA = "en-AU-NatashaNeural"  # Female, Australian
    WILLIAM = "en-AU-WilliamNeural"  # Male, Australian


class VoiceFeedback(Enum):
    """Voice feedback types with corresponding messages"""
    READY = "ready"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    CLARIFICATION = "clarification"


# Default responses for each feedback type
DEFAULT_FEEDBACK = {
    VoiceFeedback.READY: "I'm ready to help",
    VoiceFeedback.LISTENING: "I'm listening",
    VoiceFeedback.THINKING: "Let me think about that",
    VoiceFeedback.EXECUTING: "Working on it",
    VoiceFeedback.SUCCESS: "Done!",
    VoiceFeedback.ERROR: "Something went wrong",
    VoiceFeedback.CLARIFICATION: "I need more information",
}


@dataclass
class EnhancedVoiceConfig:
    """Enhanced voice configuration"""
    # Wake word settings
    wake_words: List[str] = field(default_factory=lambda: ["hey computer", "hey agent", "okay computer"])
    use_wake_word: bool = True
    
    # Speech recognition
    language: str = "en-US"
    listen_timeout: float = 5.0
    phrase_timeout: float = 5.0
    energy_threshold: int = 4000
    pause_threshold: float = 0.8
    
    # TTS settings
    tts_voice: TTSVoice = TTSVoice.ARIA
    tts_rate: str = "+10%"
    tts_pitch: str = "+0Hz"
    
    # Feedback
    enable_sounds: bool = True
    enable_voice_feedback: bool = True
    feedback_messages: Dict[VoiceFeedback, str] = field(default_factory=lambda: DEFAULT_FEEDBACK.copy())


class EnhancedVoiceInterface:
    """
    Enhanced voice interface with:
    - Multiple TTS voice options
    - Improved noise handling
    - Customizable wake words
    - State-based feedback
    - Message bus integration
    """
    
    # System sounds for feedback
    SOUNDS = {
        "ready": "/System/Library/Sounds/Glass.aiff",
        "listening": "/System/Library/Sounds/Tink.aiff",
        "success": "/System/Library/Sounds/Pop.aiff",
        "error": "/System/Library/Sounds/Basso.aiff",
        "notification": "/System/Library/Sounds/Ping.aiff",
    }
    
    def __init__(self, config: Optional[EnhancedVoiceConfig] = None):
        self.config = config or EnhancedVoiceConfig()
        self._recognizer = None
        self._microphone = None
        
        # State
        self.is_listening = False
        self.is_speaking = False
        self._stop_requested = False
        
        # Callbacks
        self.on_wake_word: Optional[Callable[[], None]] = None
        self.on_speech: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_state_change: Optional[Callable[[str], None]] = None
        
        # Speech queue for async speaking
        self._speech_queue = queue.Queue()
        
        # Initialize
        self._init_components()
        self._setup_event_handlers()
        
        logger.info("Enhanced voice interface initialized")
    
    def _init_components(self):
        """Initialize speech recognition components"""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            
            # Configure recognizer
            self._recognizer.energy_threshold = self.config.energy_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = self.config.pause_threshold
            
            # Test microphone
            self._microphone = sr.Microphone()
            
            logger.info("Speech recognition initialized")
        except ImportError:
            logger.warning("speech_recognition not installed")
            self._recognizer = None
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            self._recognizer = None
    
    def _setup_event_handlers(self):
        """Subscribe to message bus events for voice feedback"""
        # Provide voice feedback for agent events
        message_bus.subscribe(EventType.TASK_STARTED, self._on_task_started)
        message_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
        message_bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)
        message_bus.subscribe(EventType.STEP_STARTED, self._on_step_started)
    
    def _on_task_started(self, event):
        """Handle task started event"""
        if self.config.enable_sounds:
            self.play_sound("notification")
    
    def _on_task_completed(self, event):
        """Handle task completed event"""
        if self.config.enable_sounds:
            self.play_sound("success")
    
    def _on_task_failed(self, event):
        """Handle task failed event"""
        if self.config.enable_sounds:
            self.play_sound("error")
    
    def _on_step_started(self, event):
        """Handle step started event"""
        pass  # Can add step-specific feedback if desired
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def is_available(self) -> bool:
        """Check if voice interface is available"""
        return self._recognizer is not None
    
    def set_voice(self, voice: TTSVoice):
        """Change TTS voice"""
        self.config.tts_voice = voice
        logger.info(f"Voice changed to: {voice.value}")
    
    def set_wake_words(self, wake_words: List[str]):
        """Set custom wake words"""
        self.config.wake_words = [w.lower() for w in wake_words]
        logger.info(f"Wake words set to: {wake_words}")
    
    def get_available_voices(self) -> List[str]:
        """Get list of available TTS voices"""
        return [v.value for v in TTSVoice]
    
    # =========================================================================
    # Speech Recognition
    # =========================================================================
    
    def listen_once(
        self,
        timeout: Optional[float] = None,
        with_feedback: bool = True
    ) -> Optional[str]:
        """
        Listen for a single phrase.
        
        Args:
            timeout: Maximum time to wait
            with_feedback: Play listening sound
        
        Returns:
            Transcribed text or None
        """
        if not self._recognizer:
            return None
        
        import speech_recognition as sr
        
        try:
            if with_feedback and self.config.enable_sounds:
                self.play_sound("listening")
            
            with self._microphone as source:
                # Quick ambient noise adjustment
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                self.is_listening = True
                self._notify_state("listening")
                
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout or self.config.listen_timeout,
                    phrase_time_limit=self.config.phrase_timeout
                )
                
                self.is_listening = False
            
            # Transcribe using Google
            text = self._recognizer.recognize_google(
                audio,
                language=self.config.language
            )
            
            logger.info(f"Recognized: {text}")
            return text.strip()
            
        except sr.WaitTimeoutError:
            logger.debug("Listen timeout")
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
        except sr.RequestError as e:
            logger.error(f"Recognition service error: {e}")
            if self.on_error:
                self.on_error(f"Speech recognition unavailable")
        except Exception as e:
            logger.error(f"Listen error: {e}")
        finally:
            self.is_listening = False
        
        return None
    
    def listen_for_wake_word(self, timeout: float = 30.0) -> bool:
        """
        Listen for any configured wake word.
        
        Returns:
            True if wake word detected
        """
        end_time = time.time() + timeout
        
        while time.time() < end_time and not self._stop_requested:
            text = self.listen_once(timeout=5.0, with_feedback=False)
            
            if text:
                text_lower = text.lower()
                for wake_word in self.config.wake_words:
                    if wake_word in text_lower:
                        logger.info(f"Wake word detected: {wake_word}")
                        message_bus.publish(EventType.VOICE_WAKE_WORD, {"wake_word": wake_word}, "voice")
                        
                        if self.on_wake_word:
                            self.on_wake_word()
                        return True
        
        return False
    
    # =========================================================================
    # Text-to-Speech
    # =========================================================================
    
    def speak(self, text: str, wait: bool = True, voice: Optional[TTSVoice] = None):
        """
        Speak text using Edge TTS.
        
        Args:
            text: Text to speak
            wait: Wait for speech to complete
            voice: Override default voice
        """
        if not text:
            return
        
        self.is_speaking = True
        message_bus.publish(EventType.VOICE_SPEAKING_START, {"text": text}, "voice")
        
        try:
            import edge_tts
            import tempfile
            import subprocess
            import os
            
            voice_name = (voice or self.config.tts_voice).value
            
            async def generate_speech():
                communicate = edge_tts.Communicate(
                    text,
                    voice_name,
                    rate=self.config.tts_rate,
                    pitch=self.config.tts_pitch
                )
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name
                
                await communicate.save(temp_path)
                return temp_path
            
            temp_path = asyncio.run(generate_speech())
            
            # Play using afplay (macOS)
            if wait:
                subprocess.run(["afplay", temp_path], check=True)
                os.unlink(temp_path)
            else:
                subprocess.Popen(["afplay", temp_path])
                # Clean up later
                threading.Timer(
                    10.0,
                    lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None
                ).start()
                
        except ImportError:
            logger.warning("edge_tts not installed")
            print(f"[AGENT] {text}")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            print(f"[AGENT] {text}")
        finally:
            self.is_speaking = False
            message_bus.publish(EventType.VOICE_SPEAKING_END, {}, "voice")
    
    def speak_async(self, text: str, voice: Optional[TTSVoice] = None):
        """Speak without blocking"""
        threading.Thread(
            target=self.speak,
            args=(text, True, voice),
            daemon=True
        ).start()
    
    def give_feedback(self, feedback_type: VoiceFeedback, custom_message: Optional[str] = None):
        """
        Give voice feedback for a state.
        
        Args:
            feedback_type: Type of feedback
            custom_message: Override default message
        """
        if not self.config.enable_voice_feedback:
            return
        
        message = custom_message or self.config.feedback_messages.get(
            feedback_type,
            DEFAULT_FEEDBACK[feedback_type]
        )
        
        # Play sound
        if self.config.enable_sounds:
            sound = {
                VoiceFeedback.READY: "ready",
                VoiceFeedback.LISTENING: "listening",
                VoiceFeedback.SUCCESS: "success",
                VoiceFeedback.ERROR: "error",
            }.get(feedback_type)
            
            if sound:
                self.play_sound(sound)
        
        # Speak message
        self.speak_async(message)
    
    # =========================================================================
    # Continuous Listening
    # =========================================================================
    
    def start_continuous_listen(
        self,
        callback: Callable[[str], None],
        use_wake_word: Optional[bool] = None
    ):
        """
        Start continuous listening in background.
        
        Args:
            callback: Function to call with recognized text
            use_wake_word: Override config setting
        """
        use_wake = use_wake_word if use_wake_word is not None else self.config.use_wake_word
        self.on_speech = callback
        self._stop_requested = False
        
        def listen_loop():
            waiting_for_wake = use_wake
            
            while not self._stop_requested:
                try:
                    if waiting_for_wake:
                        self._notify_state("waiting_for_wake_word")
                        if self.listen_for_wake_word(timeout=10.0):
                            self.speak("Yes?")
                            waiting_for_wake = False
                    else:
                        self._notify_state("listening")
                        text = self.listen_once(timeout=10.0)
                        
                        if text:
                            text_lower = text.lower()
                            
                            # Check for wake word (acknowledgment only)
                            is_wake = any(w in text_lower for w in self.config.wake_words)
                            
                            if is_wake and len(text.split()) <= 3:
                                self.speak("I'm listening")
                            else:
                                # Strip wake word if present
                                for w in self.config.wake_words:
                                    text_lower = text_lower.replace(w, "").strip()
                                
                                # Process command
                                callback(text if text_lower == text.lower() else text_lower)
                                
                                if use_wake:
                                    waiting_for_wake = True
                                    
                except Exception as e:
                    logger.error(f"Listen loop error: {e}")
                    time.sleep(1)
            
            self._notify_state("stopped")
        
        self.is_listening = True
        threading.Thread(target=listen_loop, daemon=True).start()
        message_bus.publish(EventType.VOICE_LISTENING_START, {}, "voice")
    
    def stop_listening(self):
        """Stop continuous listening"""
        self._stop_requested = True
        self.is_listening = False
        message_bus.publish(EventType.VOICE_LISTENING_END, {}, "voice")
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def play_sound(self, sound_type: str):
        """Play a system sound"""
        sound_path = self.SOUNDS.get(sound_type)
        if sound_path:
            try:
                import subprocess
                subprocess.Popen(
                    ["afplay", sound_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
    
    def _notify_state(self, state: str):
        """Notify state change"""
        if self.on_state_change:
            self.on_state_change(state)


# Convenience function for simple use
def create_voice_interface(
    voice: TTSVoice = TTSVoice.ARIA,
    wake_words: Optional[List[str]] = None
) -> EnhancedVoiceInterface:
    """
    Create a configured voice interface.
    
    Args:
        voice: TTS voice to use
        wake_words: Custom wake words
    
    Returns:
        Configured EnhancedVoiceInterface
    """
    config = EnhancedVoiceConfig(tts_voice=voice)
    if wake_words:
        config.wake_words = wake_words
    
    return EnhancedVoiceInterface(config)
