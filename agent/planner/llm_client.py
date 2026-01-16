"""
LLM client for text generation - optional integration
"""
import json
import requests
from typing import Optional, Dict, Any, List

from ..core.config import config


class LLMClient:
    """Client for LLM text generation (optional - requires configuration)"""
    
    def __init__(self):
        self._enabled = config.ollama.is_enabled
        self.base_url = config.ollama.base_url
        self.model = config.ollama.planner_model
    
    @property
    def is_enabled(self) -> bool:
        """Check if LLM is configured"""
        return self._enabled
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 json_mode: bool = False) -> str:
        """
        Generate text response from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            json_mode: If True, request JSON formatted response
        
        Returns:
            Generated text
        
        Raises:
            RuntimeError: If LLM is not configured
        """
        if not self._enabled:
            raise RuntimeError("LLM not configured. Set ollama.base_url and ollama.planner_model in config.")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.ollama.temperature
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if json_mode:
            payload["format"] = "json"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=config.ollama.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot connect to LLM at {self.base_url}")
        except Exception as e:
            raise RuntimeError(f"LLM query failed: {e}")
    
    def chat(self, messages: List[Dict[str, str]], 
             system_prompt: Optional[str] = None,
             json_mode: bool = False) -> str:
        """
        Multi-turn chat with LLM.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Optional system instructions
            json_mode: If True, request JSON formatted response
        
        Returns:
            Generated response
        
        Raises:
            RuntimeError: If LLM is not configured
        """
        if not self._enabled:
            raise RuntimeError("LLM not configured. Set ollama.base_url and ollama.planner_model in config.")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.ollama.temperature
            }
        }
        
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages
        
        if json_mode:
            payload["format"] = "json"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=config.ollama.timeout
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot connect to LLM at {self.base_url}")
        except Exception as e:
            raise RuntimeError(f"LLM chat failed: {e}")
    
    def is_available(self) -> bool:
        """Check if LLM is configured and running"""
        if not self._enabled:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return self.model in models or self.model.split(":")[0] in [m.split(":")[0] for m in models]
            return False
        except:
            return False

