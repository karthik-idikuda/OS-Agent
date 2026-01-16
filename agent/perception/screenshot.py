"""
Screenshot capture module
"""
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.config import SCREENSHOTS_DIR


class ScreenCapture:
    """Captures screenshots of the macOS screen"""
    
    def __init__(self, save_dir: Optional[Path] = None):
        self.save_dir = save_dir or SCREENSHOTS_DIR
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def capture(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture full screen screenshot.
        
        Returns:
            Dict with filepath, dimensions, hash
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screen_{timestamp}.png"
        
        filepath = self.save_dir / filename
        
        # Use macOS screencapture (silent mode with -x)
        result = subprocess.run(
            ["screencapture", "-x", str(filepath)],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Screenshot failed: {result.stderr.decode()}")
        
        # Get dimensions and hash
        dimensions = self._get_image_dimensions(filepath)
        file_hash = self._get_file_hash(filepath)
        
        return {
            "filepath": str(filepath),
            "filename": filename,
            "width": dimensions[0],
            "height": dimensions[1],
            "hash": file_hash,
            "timestamp": datetime.now().isoformat()
        }
    
    def capture_region(self, x: int, y: int, width: int, height: int, 
                       filename: Optional[str] = None) -> Dict[str, Any]:
        """Capture a specific region of the screen"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"region_{timestamp}.png"
        
        filepath = self.save_dir / filename
        
        # Use screencapture with region flag
        result = subprocess.run(
            ["screencapture", "-x", "-R", f"{x},{y},{width},{height}", str(filepath)],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Region capture failed: {result.stderr.decode()}")
        
        return {
            "filepath": str(filepath),
            "filename": filename,
            "width": width,
            "height": height,
            "region": (x, y, width, height),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_image_dimensions(self, filepath: Path) -> tuple:
        """Get image dimensions using sips (macOS)"""
        try:
            result = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(filepath)],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split('\n')
            width = int([l for l in lines if 'pixelWidth' in l][0].split(':')[1].strip())
            height = int([l for l in lines if 'pixelHeight' in l][0].split(':')[1].strip())
            return (width, height)
        except Exception:
            return (0, 0)
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of file for change detection"""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    
    def cleanup_old(self, days: int = 7):
        """Remove screenshots older than specified days"""
        import time
        cutoff = time.time() - (days * 86400)
        
        for file in self.save_dir.glob("*.png"):
            if file.stat().st_mtime < cutoff:
                file.unlink()
