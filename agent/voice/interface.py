"""
Voice Interface - Speech recognition and text-to-speech
"""
import asyncio
import logging
import threading
import queue
import time
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Voice configuration"""
    wake_word: str = "hey computer"
    language: str = "en-US"
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: str = "+10%"
    listen_timeout: float = 5.0
    phrase_timeout: float = 3.0


class VoiceInterface:
    """
    Voice interface with:
    - Speech recognition using Google Speech Recognition
    - Text-to-speech using Edge TTS
    - Wake word detection
    - Continuous listening mode
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._recognizer = None
        self._microphone = None
        
        # State
        self.is_listening = False
        self.is_speaking = False
        
        # Callbacks
        self.on_wake_word: Optional[Callable[[], None]] = None
        self.on_speech: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Audio queue for TTS
        self._speech_queue = queue.Queue()
        self._speech_thread: Optional[threading.Thread] = None
        
        self._init_components()
    
    def _init_components(self):
        """Initialize speech recognition components"""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 4000
            self._recognizer.dynamic_energy_threshold = True
            
            # Test microphone
            self._microphone = sr.Microphone()
            logger.info("Voice components initialized")
        except ImportError:
            logger.warning("speech_recognition not installed. Run: pip install SpeechRecognition")
            self._recognizer = None
        except Exception as e:
            logger.error(f"Microphone initialization error: {e}")
            self._recognizer = None
    
    def is_available(self) -> bool:
        """Check if voice interface is available"""
        return self._recognizer is not None
    
    def listen_once(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Listen for a single phrase.
        
        Args:
            timeout: Maximum time to wait for speech
        
        Returns:
            Transcribed text or None
        """
        if not self._recognizer:
            return None
        
        import speech_recognition as sr
        
        try:
            with self._microphone as source:
                logger.debug("Adjusting for ambient noise...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                logger.debug("Listening...")
                self.is_listening = True
                
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout or self.config.listen_timeout,
                    phrase_time_limit=self.config.phrase_timeout
                )
                
                self.is_listening = False
            
            # Transcribe
            text = self._recognizer.recognize_google(
                audio,
                language=self.config.language
            )
            
            logger.info(f"Recognized: {text}")
            return text.lower().strip()
            
        except sr.WaitTimeoutError:
            logger.debug("Listen timeout")
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            if self.on_error:
                self.on_error(f"Speech recognition unavailable: {e}")
        except Exception as e:
            logger.error(f"Listen error: {e}")
        finally:
            self.is_listening = False
        
        return None
    
    def listen_for_wake_word(self, timeout: float = 30.0) -> bool:
        """
        Listen for wake word.
        
        Args:
            timeout: Maximum time to wait
        
        Returns:
            True if wake word detected
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            text = self.listen_once(timeout=5.0)
            
            if text and self.config.wake_word.lower() in text.lower():
                logger.info("Wake word detected!")
                if self.on_wake_word:
                    self.on_wake_word()
                return True
        
        return False
    
    def speak(self, text: str, wait: bool = True):
        """
        Speak text using Edge TTS.
        
        Args:
            text: Text to speak
            wait: Wait for speech to complete
        """
        if not text:
            return
        
        logger.info(f"Speaking: {text}")
        self.is_speaking = True
        
        try:
            import edge_tts
            import tempfile
            import subprocess
            import os
            
            # Generate speech
            async def generate_speech():
                communicate = edge_tts.Communicate(
                    text,
                    self.config.tts_voice,
                    rate=self.config.tts_rate
                )
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name
                
                await communicate.save(temp_path)
                return temp_path
            
            # Run async generation
            temp_path = asyncio.run(generate_speech())
            
            # Play audio using afplay (macOS)
            if wait:
                subprocess.run(["afplay", temp_path], check=True)
                os.unlink(temp_path)
            else:
                # Play in background
                subprocess.Popen(["afplay", temp_path])
                # Schedule cleanup
                threading.Timer(10.0, lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None).start()
                
        except ImportError:
            logger.warning("edge_tts not installed. Run: pip install edge-tts")
            print(f"[AGENT] {text}")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            print(f"[AGENT] {text}")
        finally:
            self.is_speaking = False
    
    def speak_async(self, text: str):
        """Speak without blocking"""
        threading.Thread(
            target=self.speak,
            args=(text, True),
            daemon=True
        ).start()
    
    def start_continuous_listen(
        self,
        callback: Callable[[str], None],
        use_wake_word: bool = True
    ):
        """
        Start continuous listening in background.
        
        Args:
            callback: Function to call with recognized text
            use_wake_word: Whether to wait for wake word first
        """
        self.on_speech = callback
        
        def listen_loop():
            waiting_for_wake = use_wake_word
            
            while self.is_listening:
                try:
                    if waiting_for_wake:
                        if self.listen_for_wake_word(timeout=10.0):
                            self.speak("Yes?")
                            waiting_for_wake = False
                    else:
                        text = self.listen_once(timeout=10.0)
                        if text:
                            if self.config.wake_word.lower() in text.lower():
                                # Just acknowledgment
                                self.speak("I'm listening")
                            else:
                                # Process command
                                callback(text)
                                if use_wake_word:
                                    waiting_for_wake = True
                except Exception as e:
                    logger.error(f"Listen loop error: {e}")
                    time.sleep(1)
        
        self.is_listening = True
        threading.Thread(target=listen_loop, daemon=True).start()
    
    def stop_listening(self):
        """Stop continuous listening"""
        self.is_listening = False
    
    def play_sound(self, sound_type: str):
        """
        Play a notification sound.
        
        Args:
            sound_type: Type of sound (ready, success, error, listening)
        """
        sounds = {
            "ready": "/System/Library/Sounds/Glass.aiff",
            "success": "/System/Library/Sounds/Pop.aiff",
            "error": "/System/Library/Sounds/Basso.aiff",
            "listening": "/System/Library/Sounds/Tink.aiff"
        }
        
        sound_path = sounds.get(sound_type)
        if sound_path:
            try:
                import subprocess
                subprocess.Popen(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass


class SimpleVoiceInput:
    """
    Simple voice input without continuous listening.
    For use in command-line mode.
    """
    
    def __init__(self):
        self._recognizer = None
        self._init()
    
    def _init(self):
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 4000
        except ImportError:
            pass
    
    def get_input(self, prompt: str = "Listening...") -> Optional[str]:
        """Get voice input with visual prompt"""
        if not self._recognizer:
            print("Voice input not available. Please type instead.")
            return input("> ").strip()
        
        import speech_recognition as sr
        
        print(prompt)
        
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(source, timeout=10, phrase_time_limit=10)
            
            text = self._recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("No speech detected")
        except sr.UnknownValueError:
            print("Could not understand audio")
        except Exception as e:
            print(f"Error: {e}")
        
        return None
