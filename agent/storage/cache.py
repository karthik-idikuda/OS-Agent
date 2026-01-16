"""
Screenshot Cache - Manages screenshot storage with auto-cleanup

Provides:
- Screenshot file management
- Metadata tracking
- Automatic cleanup of old files
- Size-based cache limits
"""
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import shutil

from ..core.config import SCREENSHOTS_DIR

logger = logging.getLogger(__name__)


class ScreenshotCache:
    """
    Manages screenshot file cache with automatic cleanup.
    
    Features:
    - Saves screenshots with timestamps
    - Tracks metadata
    - Auto-deletes files older than retention period
    - Enforces maximum cache size
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        retention_days: int = 7,
        max_size_mb: int = 500
    ):
        """
        Initialize screenshot cache.
        
        Args:
            cache_dir: Directory to store screenshots
            retention_days: Days to keep screenshots
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir) if cache_dir else SCREENSHOTS_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = retention_days
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        logger.debug(f"Screenshot cache at {self.cache_dir}")
    
    def save(
        self,
        image_path: str,
        prefix: str = "screenshot"
    ) -> Dict:
        """
        Save a screenshot to the cache.
        
        Args:
            image_path: Path to source image
            prefix: Filename prefix
        
        Returns:
            Dict with filepath and metadata
        """
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"Source image not found: {image_path}")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}{source.suffix}"
        dest = self.cache_dir / filename
        
        # Copy file
        shutil.copy2(source, dest)
        
        # Get file stats
        stat = dest.stat()
        
        logger.debug(f"Saved screenshot: {filename}")
        
        return {
            "filepath": str(dest),
            "filename": filename,
            "size_bytes": stat.st_size,
            "created_at": datetime.now().isoformat()
        }
    
    def get(self, filename: str) -> Optional[str]:
        """
        Get screenshot filepath by filename.
        
        Returns:
            File path if exists, None otherwise
        """
        path = self.cache_dir / filename
        return str(path) if path.exists() else None
    
    def list_screenshots(self, limit: int = 50) -> List[Dict]:
        """
        List cached screenshots.
        
        Args:
            limit: Maximum files to return
        
        Returns:
            List of screenshot metadata dicts
        """
        files = []
        
        for path in sorted(self.cache_dir.glob("*.png"), reverse=True)[:limit]:
            stat = path.stat()
            files.append({
                "filepath": str(path),
                "filename": path.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return files
    
    def cleanup(self, older_than_days: Optional[int] = None) -> Dict:
        """
        Remove old screenshots.
        
        Args:
            older_than_days: Days threshold (default: retention_days)
        
        Returns:
            Dict with deleted count and freed bytes
        """
        days = older_than_days or self.retention_days
        cutoff = datetime.now() - timedelta(days=days)
        
        deleted_count = 0
        freed_bytes = 0
        
        for path in self.cache_dir.glob("*.png"):
            try:
                stat = path.stat()
                created = datetime.fromtimestamp(stat.st_ctime)
                
                if created < cutoff:
                    freed_bytes += stat.st_size
                    path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        
        logger.info(f"Cleanup: deleted {deleted_count} files, freed {freed_bytes / 1024:.1f} KB")
        
        return {
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes
        }
    
    def enforce_size_limit(self) -> Dict:
        """
        Enforce maximum cache size by deleting oldest files.
        
        Returns:
            Dict with deleted count and freed bytes
        """
        total_size = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.png")
        )
        
        if total_size <= self.max_size_bytes:
            return {"deleted_count": 0, "freed_bytes": 0}
        
        # Get files sorted by creation time (oldest first)
        files = sorted(
            self.cache_dir.glob("*.png"),
            key=lambda p: p.stat().st_ctime
        )
        
        deleted_count = 0
        freed_bytes = 0
        
        for path in files:
            if total_size <= self.max_size_bytes:
                break
            
            try:
                size = path.stat().st_size
                path.unlink()
                total_size -= size
                freed_bytes += size
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        
        logger.info(f"Size limit: deleted {deleted_count} files, freed {freed_bytes / 1024:.1f} KB")
        
        return {
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        files = list(self.cache_dir.glob("*.png"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "usage_percent": round(total_size / self.max_size_bytes * 100, 1) if self.max_size_bytes > 0 else 0,
            "cache_dir": str(self.cache_dir)
        }
    
    def clear(self) -> Dict:
        """
        Clear all cached screenshots.
        
        Returns:
            Dict with deleted count
        """
        deleted_count = 0
        
        for path in self.cache_dir.glob("*.png"):
            try:
                path.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        
        logger.info(f"Cache cleared: deleted {deleted_count} files")
        
        return {"deleted_count": deleted_count}


# Global cache instance
screenshot_cache = ScreenshotCache()
