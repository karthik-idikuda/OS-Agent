"""
Vision module using LLaVA for screen analysis
"""
import json
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..core.config import config
from ..core.models import ScreenAnalysis, ScreenElement
from .screenshot import ScreenCapture


class VisionAnalyzer:
    """Analyzes screenshots using LLaVA vision model via Ollama"""
    
    def __init__(self):
        self.base_url = config.ollama.base_url
        self.model = config.ollama.vision_model
        self.screen_capture = ScreenCapture()
    
    def analyze_screen(self, screenshot_path: Optional[str] = None) -> ScreenAnalysis:
        """
        Capture and analyze current screen.
        
        Returns:
            ScreenAnalysis with summary and detected elements
        """
        # Capture screenshot if not provided
        if screenshot_path is None:
            capture = self.screen_capture.capture()
            screenshot_path = capture["filepath"]
            width = capture["width"]
            height = capture["height"]
        else:
            # Get dimensions from existing file
            from PIL import Image
            with Image.open(screenshot_path) as img:
                width, height = img.size
        
        # Encode image
        image_b64 = self._encode_image(screenshot_path)
        
        # Analyze with LLaVA
        prompt = """Analyze this macOS screenshot. Return JSON only:
{
    "summary": "Brief description of what's on screen (active app, visible content)",
    "active_app": "Name of the focused application",
    "elements": [
        {"text": "visible text", "type": "button|input|link|text|icon", "location": "description of where"}
    ]
}
Focus on interactive elements. JSON only, no markdown:"""
        
        response = self._query_vision(image_b64, prompt)
        
        # Parse response
        try:
            data = self._parse_json(response)
            elements = [
                ScreenElement(
                    text=e.get("text", ""),
                    element_type=e.get("type", "unknown"),
                    bbox=(0, 0, 0, 0),  # LLaVA doesn't give precise coords
                    center=(0, 0),
                    confidence=0.7
                )
                for e in data.get("elements", [])
            ]
            
            return ScreenAnalysis(
                screenshot_path=screenshot_path,
                width=width,
                height=height,
                summary=data.get("summary", "Unable to analyze screen"),
                elements=elements,
                active_app=data.get("active_app")
            )
        except Exception as e:
            return ScreenAnalysis(
                screenshot_path=screenshot_path,
                width=width,
                height=height,
                summary=f"Analysis failed: {str(e)}",
                elements=[]
            )
    
    def find_element(self, target: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Find a specific element on screen and return its coordinates.
        
        Args:
            target: Description of element to find (e.g., "search button", "text field")
        
        Returns:
            Dict with found status and coordinates
        """
        if screenshot_path is None:
            capture = self.screen_capture.capture()
            screenshot_path = capture["filepath"]
            width = capture["width"]
            height = capture["height"]
        else:
            from PIL import Image
            with Image.open(screenshot_path) as img:
                width, height = img.size
        
        image_b64 = self._encode_image(screenshot_path)
        
        prompt = f"""Find "{target}" in this screenshot.
Return the CENTER coordinates where I should click.
Screen size is {width}x{height} pixels.

Return JSON only:
{{"found": true/false, "x": pixel_x, "y": pixel_y, "confidence": 0.0-1.0, "description": "what you found"}}

Be precise with coordinates. JSON only:"""
        
        response = self._query_vision(image_b64, prompt)
        
        try:
            data = self._parse_json(response)
            return {
                "found": data.get("found", False),
                "x": data.get("x", 0),
                "y": data.get("y", 0),
                "confidence": data.get("confidence", 0.0),
                "description": data.get("description", ""),
                "screenshot": screenshot_path
            }
        except Exception as e:
            return {
                "found": False,
                "error": str(e),
                "screenshot": screenshot_path
            }
    
    def verify_action(self, expected: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify if an expected state is visible on screen.
        
        Args:
            expected: Description of expected state (e.g., "YouTube is open", "search results visible")
        
        Returns:
            Dict with verification result
        """
        if screenshot_path is None:
            capture = self.screen_capture.capture()
            screenshot_path = capture["filepath"]
        
        image_b64 = self._encode_image(screenshot_path)
        
        prompt = f"""Verify: "{expected}"

Look at this screenshot and determine if the expected state is true.

Return JSON only:
{{"verified": true/false, "confidence": 0.0-1.0, "actual_state": "what you actually see", "reason": "why verified or not"}}

JSON only:"""
        
        response = self._query_vision(image_b64, prompt)
        
        try:
            data = self._parse_json(response)
            return {
                "verified": data.get("verified", False),
                "confidence": data.get("confidence", 0.0),
                "actual_state": data.get("actual_state", ""),
                "reason": data.get("reason", ""),
                "screenshot": screenshot_path
            }
        except Exception as e:
            return {
                "verified": False,
                "error": str(e),
                "screenshot": screenshot_path
            }
    
    def _query_vision(self, image_b64: str, prompt: str) -> str:
        """Send query to LLaVA model"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=config.ollama.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Ollama is not running. Start with: ollama serve")
        except Exception as e:
            raise RuntimeError(f"Vision query failed: {e}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from LLM response"""
        # Clean up common issues
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
