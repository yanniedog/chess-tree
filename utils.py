"""
Utility functions for the Chess Opening Explorer
"""
import chess
import json
import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import time
import threading
from queue import Queue
import gzip
import bz2
import lzma

# Centralized logger setup
_LOGGER = None
_LOG_FILE = "chess_tree.log"

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get the central logger instance, creating it if needed."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER if name is None else logging.getLogger(name)

    logger = logging.getLogger("chess_tree")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(process)d | %(threadName)s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Clear the log file at startup
    try:
        with open(_LOG_FILE, 'w') as f:
            f.write(f"=== Chess Opening Explorer Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    except Exception:
        pass  # Ignore errors if file can't be written

    # File handler (detailed log)
    file_handler = logging.FileHandler(_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (info+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _LOGGER = logger
    return logger if name is None else logging.getLogger(name)

def set_log_level(level: int):
    """Dynamically set log level for all handlers."""
    logger = get_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

@dataclass
class GameResult:
    """Represents the result of a chess game"""
    fen: str
    move: str
    result: str  # "1-0", "0-1", "1/2-1/2"
    network: str
    source_file: str
    timestamp: float

@dataclass
class MoveStats:
    """Statistics for a specific move from a position"""
    fen: str
    move: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    network: str = ""
    source_files: List[str] = None
    last_updated: float = 0.0
    evaluation_score: int = 0  # Evaluation score in centipawns
    
    def __post_init__(self):
        if self.source_files is None:
            self.source_files = []
    
    @property
    def total_games(self) -> int:
        return self.wins + self.losses + self.draws
    
    @property
    def performance_score(self) -> float:
        """Calculate performance score: (wins + 0.5 * draws) / total_games"""
        if self.total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.draws) / self.total_games
    
    @property
    def decisiveness_score(self) -> float:
        """Calculate decisiveness score: wins / (wins + losses)"""
        decisive_games = self.wins + self.losses
        if decisive_games == 0:
            return 0.0
        return self.wins / decisive_games
    
    @property
    def confidence_level(self) -> str:
        """Get confidence level based on game count"""
        if self.total_games < 10:
            return "low"
        elif self.total_games < 50:
            return "medium"
        else:
            return "high"

def normalize_fen(fen: str) -> str:
    """
    Normalize FEN by removing halfmove clock and move number
    to deduplicate transpositions
    """
    board = chess.Board(fen)
    # Reconstruct FEN without move counters
    fen_parts = board.fen().split(' ')[:4]
    return ' '.join(fen_parts + ['0', '1'])

def get_legal_moves(fen: str) -> List[str]:
    """Get all legal moves from a position in UCI format"""
    board = chess.Board(fen)
    return [move.uci() for move in board.legal_moves]

def is_valid_fen(fen: str) -> bool:
    """Check if FEN string is valid"""
    try:
        chess.Board(fen)
        return True
    except ValueError:
        return False

def calculate_hash(data: str) -> str:
    """Calculate SHA256 hash of data"""
    return hashlib.sha256(data.encode()).hexdigest()

def format_time(seconds: float) -> str:
    """Format time in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def format_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"

class RateLimiter:
    """Simple rate limiter for network requests"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = threading.Lock()
    
    def acquire(self) -> bool:
        """Try to acquire a request slot"""
        with self.lock:
            now = time.time()
            # Remove old requests
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.time_window]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        while not self.acquire():
            time.sleep(0.1)

class ProgressTracker:
    """Track progress of operations"""
    
    def __init__(self, total: int, description: str = ""):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update(self, increment: int = 1):
        """Update progress"""
        with self.lock:
            self.current += increment
            elapsed = time.time() - self.start_time
            if self.current > 0:
                eta = (elapsed / self.current) * (self.total - self.current)
                get_logger().info(f"{self.description}: {self.current}/{self.total} "
                          f"({self.current/self.total*100:.1f}%) ETA: {format_time(eta)}")
    
    def complete(self):
        """Mark as complete"""
        elapsed = time.time() - self.start_time
        get_logger().info(f"{self.description}: Completed in {format_time(elapsed)}")

def compress_data(data: bytes, algorithm: str = "gzip") -> bytes:
    """Compress data using specified algorithm"""
    if algorithm == "gzip":
        return gzip.compress(data)
    elif algorithm == "bz2":
        return bz2.compress(data)
    elif algorithm == "lzma":
        return lzma.compress(data)
    else:
        raise ValueError(f"Unsupported compression algorithm: {algorithm}")

def decompress_data(data: bytes, algorithm: str = "gzip") -> bytes:
    """Decompress data using specified algorithm"""
    if algorithm == "gzip":
        return gzip.decompress(data)
    elif algorithm == "bz2":
        return bz2.decompress(data)
    elif algorithm == "lzma":
        return lzma.decompress(data)
    else:
        raise ValueError(f"Unsupported compression algorithm: {algorithm}")

def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """Safely load JSON data"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        get_logger().error(f"Failed to parse JSON: {e}")
        return None

def validate_network_version(network: str) -> bool:
    """Validate LCZero network version format"""
    # Expected format: T70, T80, etc.
    return network.startswith('T') and network[1:].isdigit()

def get_confidence_color(confidence: str) -> str:
    """Get color for confidence level"""
    colors = {
        "low": "#ff4444",      # Red
        "medium": "#ffaa00",    # Yellow
        "high": "#44ff44"       # Green
    }
    return colors.get(confidence, "#888888")

def log_and_print(message: str, level: int = logging.INFO):
    """Log message and also print to console"""
    logger = get_logger()
    logger.log(level, message)
    print(message) 

def fetch_lichess_api(fen: str, endpoint: str = "lichess", multi_pv: int = 1) -> dict:
    """
    Fetch data from Lichess API endpoints for a given FEN.
    endpoint: 'lichess', 'masters', or 'cloud-eval'
    multi_pv: Only used for cloud-eval endpoint
    Returns parsed JSON data.
    Aborts to command line on any error or warning.
    Logs all requests, responses, and errors.
    """
    import requests
    import sys
    logger = get_logger()
    base_urls = {
        "lichess": "https://explorer.lichess.ovh/lichess?variant=standard&fen={}",
        "masters": "https://explorer.lichess.ovh/masters?variant=standard&fen={}",
        "cloud-eval": "https://lichess.org/api/cloud-eval?fen={}&multiPv={}"
    }
    try:
        if endpoint == "cloud-eval":
            url = base_urls[endpoint].format(fen, multi_pv)
        else:
            url = base_urls[endpoint].format(fen)
        logger.info(f"Fetching Lichess API: {url}")
        response = requests.get(url, timeout=10)
        logger.info(f"Response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Lichess API error: {response.status_code} {response.text}")
            print(f"Error: Lichess API returned status {response.status_code}")
            sys.exit(1)
        data = response.json()
        logger.info(f"Lichess API response: {json.dumps(data)[:1000]}")
        return data
    except Exception as e:
        logger.exception(f"Exception during Lichess API fetch: {e}")
        print(f"Exception during Lichess API fetch: {e}")
        sys.exit(1) 