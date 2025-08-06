"""
Configuration settings for the Chess Opening Explorer
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CacheConfig:
    """Cache configuration settings"""
    max_size_gb: float = 0.05  # Reduced to 50MB for better compatibility
    lru_eviction: bool = True
    cache_dir: Path = Path("cache")
    lmdb_path: Path = Path("cache/data.lmdb")
    sqlite_path: Path = Path("cache/stats.db")

@dataclass
class NetworkConfig:
    """Network and download settings"""
    timeout_seconds: int = 30
    max_retries: int = 3
    bandwidth_limit_mbps: float = 10.0
    chunk_size: int = 8192
    resume_downloads: bool = True

@dataclass
class EngineConfig:
    """Engine analysis settings"""
    default_engine: str = "stockfish"
    engine_time_ms: int = 1000
    engine_depth: int = 20
    engine_threads: int = 4

@dataclass
class UIConfig:
    """User interface settings"""
    board_size: int = 400
    theme: str = "default"
    auto_prefetch: bool = True
    prefetch_moves: int = 3
    confidence_thresholds: Dict[str, int] = None

    def __post_init__(self):
        if self.confidence_thresholds is None:
            self.confidence_thresholds = {
                "low": 10,
                "medium": 50,
                "high": 100
            }

@dataclass
class DataConfig:
    """Data source and processing settings"""
    lczero_base_url: str = "https://lczero.org/play/networks/"
    archive_index_url: str = "https://lczero.org/play/networks/index.json"
    max_games_per_fen: int = 1000
    streaming_threshold: int = 100
    normalize_fen: bool = True
    deduplicate_transpositions: bool = True

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.cache = CacheConfig()
        self.network = NetworkConfig()
        self.engine = EngineConfig()
        self.ui = UIConfig()
        self.data = DataConfig()
        
        # Ensure cache directory exists
        self.cache.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_path(self, filename: str) -> Path:
        """Get path for cache file"""
        return self.cache.cache_dir / filename
    
    def get_archive_path(self, filename: str) -> Path:
        """Get path for archive file"""
        return self.cache.cache_dir / "archives" / filename

# Global configuration instance
config = Config() 