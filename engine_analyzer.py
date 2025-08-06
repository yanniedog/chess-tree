"""
Engine analysis module for real-time chess evaluation
"""
import chess
import chess.engine
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json

from config import config
from utils import get_logger, fetch_lichess_api

# Initialize logger
logger = get_logger()

@dataclass
class EngineEvaluation:
    """Represents an engine evaluation for a position"""
    fen: str
    move: str
    score: float  # Centipawns
    depth: int
    time_ms: int
    engine: str
    timestamp: float

@dataclass
class EngineMove:
    """Represents a move with engine evaluation"""
    move: str
    score: float
    depth: int
    time_ms: int
    pv: List[str] = None  # Principal variation
    
    def __post_init__(self):
        if self.pv is None:
            self.pv = []

class EngineManager:
    """Manages chess engine analysis"""
    
    def __init__(self):
        self.engines: Dict[str, chess.engine.SimpleEngine] = {}
        self.analysis_queue = []
        self.analyzing = False
        self.lock = threading.Lock()
        self.init_engines()
    
    def init_engines(self):
        """Initialize available chess engines"""
        # Try to find Stockfish
        stockfish_paths = [
            "stockfish",
            "stockfish.exe",
            "/usr/local/bin/stockfish",
            "/usr/bin/stockfish",
            "C:/Program Files/Stockfish/stockfish.exe"
        ]
        
        for path in stockfish_paths:
            try:
                engine = chess.engine.SimpleEngine.popen_uci(path)
                # Test the engine
                board = chess.Board()
                result = engine.analyse(board, chess.engine.Limit(time=0.1))
                engine.quit()
                
                # If we get here, the engine works
                logger.info(f"Found Stockfish at: {path}")
                self.engines["stockfish"] = path
                break
            except Exception as e:
                logger.debug(f"Stockfish not found at {path}: {e}")
                continue
        
        if not self.engines:
            logger.info("No chess engines found. Engine analysis will be unavailable.")
            logger.info("To enable engine analysis, install Stockfish from https://stockfishchess.org/")
            logger.info("The application will work without engines for opening exploration.")
    
    def get_engine(self, engine_name: str = "stockfish") -> Optional[chess.engine.SimpleEngine]:
        """Get a chess engine instance"""
        if engine_name not in self.engines:
            logger.debug(f"Engine {engine_name} not available")
            return None
        
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.engines[engine_name])
            return engine
        except Exception as e:
            logger.debug(f"Failed to start engine {engine_name}: {e}")
            return None
    
    def analyze_position(self, fen: str, engine_name: str = "stockfish", 
                        time_limit: int = None, depth_limit: int = None) -> List[EngineMove]:
        """Analyze a position and return top moves with evaluations"""
        engine = self.get_engine(engine_name)
        if not engine:
            return []
        
        try:
            board = chess.Board(fen)
            
            # Set analysis limits
            limits = chess.engine.Limit()
            if time_limit:
                limits.time = time_limit / 1000.0  # Convert to seconds
            if depth_limit:
                limits.depth = depth_limit
            
            # Get analysis
            result = engine.analyse(board, limits, multipv=10)
            
            moves = []
            for pv_info in result:
                if "pv" in pv_info and pv_info["pv"]:
                    move = pv_info["pv"][0]
                    score = pv_info.get("score", chess.engine.Score(0))
                    
                    # Convert score to centipawns
                    if score.is_mate():
                        score_cp = 10000 if score.mate() > 0 else -10000
                    else:
                        score_cp = score.score()
                    
                    engine_move = EngineMove(
                        move=move.uci(),
                        score=score_cp,
                        depth=pv_info.get("depth", 0),
                        time_ms=int(pv_info.get("time", 0) * 1000),
                        pv=[m.uci() for m in pv_info["pv"]]
                    )
                    moves.append(engine_move)
            
            # Fetch Lichess cloud eval for this FEN
            try:
                lichess_eval = fetch_lichess_api(fen, endpoint="cloud-eval")
                logger.info(f"Fetched Lichess cloud eval for FEN {fen}: {lichess_eval}")
                self.last_lichess_eval = lichess_eval
            except Exception as e:
                logger.error(f"Failed to fetch Lichess cloud eval for FEN {fen}: {e}")
            
            return moves
            
        except Exception as e:
            logger.debug(f"Engine analysis failed: {e}")
            return []
        finally:
            engine.quit()
    
    def analyze_move(self, fen: str, move: str, engine_name: str = "stockfish",
                    time_limit: int = None, depth_limit: int = None) -> Optional[EngineEvaluation]:
        """Analyze a specific move from a position"""
        engine = self.get_engine(engine_name)
        if not engine:
            return None
        
        try:
            board = chess.Board(fen)
            chess_move = chess.Move.from_uci(move)
            
            if chess_move not in board.legal_moves:
                logger.error(f"Invalid move {move} for position {fen}")
                return None
            
            # Make the move
            board.push(chess_move)
            
            # Analyze the resulting position
            limits = chess.engine.Limit()
            if time_limit:
                limits.time = time_limit / 1000.0
            if depth_limit:
                limits.depth = depth_limit
            
            result = engine.analyse(board, limits)
            
            score = result.get("score", chess.engine.Score(0))
            if score.is_mate():
                score_cp = 10000 if score.mate() > 0 else -10000
            else:
                score_cp = score.score()
            
            # Fetch Lichess cloud eval for this FEN
            try:
                lichess_eval = fetch_lichess_api(fen, endpoint="cloud-eval")
                logger.info(f"Fetched Lichess cloud eval for FEN {fen}: {lichess_eval}")
                self.last_lichess_eval = lichess_eval
            except Exception as e:
                logger.error(f"Failed to fetch Lichess cloud eval for FEN {fen}: {e}")
            
            return EngineEvaluation(
                fen=fen,
                move=move,
                score=score_cp,
                depth=result.get("depth", 0),
                time_ms=int(result.get("time", 0) * 1000),
                engine=engine_name,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Move analysis failed: {e}")
            return None
        finally:
            engine.quit()
    
    def get_engine_info(self, engine_name: str = "stockfish") -> Dict:
        """Get information about an engine"""
        engine = self.get_engine(engine_name)
        if not engine:
            return {}
        
        try:
            info = {}
            
            # Get engine name
            engine.configure({"UCI_ShowCurrLine": "true"})
            engine.configure({"UCI_LimitStrength": "false"})
            
            # Try to get some basic info
            try:
                engine.ping()
                info["status"] = "available"
            except:
                info["status"] = "error"
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get engine info: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            engine.quit()
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines"""
        return list(self.engines.keys())
    
    def test_engine(self, engine_name: str = "stockfish") -> bool:
        """Test if an engine is working properly"""
        engine = self.get_engine(engine_name)
        if not engine:
            return False
        
        try:
            # Simple test position
            board = chess.Board()
            result = engine.analyse(board, chess.engine.Limit(time=0.1))
            return True
        except Exception as e:
            logger.error(f"Engine test failed: {e}")
            return False
        finally:
            engine.quit()

class AnalysisManager:
    """Manages background analysis tasks"""
    
    def __init__(self, engine_manager: EngineManager):
        self.engine_manager = engine_manager
        self.analysis_results: Dict[str, List[EngineMove]] = {}
        self.analysis_queue = []
        self.analyzing = False
        self.lock = threading.Lock()
    
    def queue_analysis(self, fen: str, engine_name: str = "stockfish",
                      time_limit: int = None, depth_limit: int = None):
        """Queue a position for analysis"""
        with self.lock:
            self.analysis_queue.append({
                "fen": fen,
                "engine": engine_name,
                "time_limit": time_limit,
                "depth_limit": depth_limit
            })
    
    def get_analysis(self, fen: str) -> Optional[List[EngineMove]]:
        """Get cached analysis for a position"""
        with self.lock:
            return self.analysis_results.get(fen)
    
    def start_background_analysis(self):
        """Start background analysis thread"""
        if self.analyzing:
            return
        
        self.analyzing = True
        thread = threading.Thread(target=self._analysis_worker, daemon=True)
        thread.start()
    
    def _analysis_worker(self):
        """Background analysis worker"""
        while self.analyzing:
            with self.lock:
                if not self.analysis_queue:
                    time.sleep(0.1)
                    continue
                
                task = self.analysis_queue.pop(0)
            
            try:
                fen = task["fen"]
                engine_name = task.get("engine", "stockfish")
                time_limit = task.get("time_limit")
                depth_limit = task.get("depth_limit")
                
                logger.info(f"Analyzing position: {fen[:50]}...")
                moves = self.engine_manager.analyze_position(
                    fen, engine_name, time_limit, depth_limit
                )
                
                with self.lock:
                    self.analysis_results[fen] = moves
                
                logger.info(f"Analysis complete for position: {fen[:50]}...")
                
            except Exception as e:
                logger.error(f"Background analysis failed: {e}")
            
            time.sleep(0.1)  # Small delay to prevent CPU overload
    
    def stop_background_analysis(self):
        """Stop background analysis"""
        self.analyzing = False
    
    def clear_cache(self):
        """Clear analysis cache"""
        with self.lock:
            self.analysis_results.clear()
            self.analysis_queue.clear()

# Global engine manager instance
engine_manager = EngineManager()
analysis_manager = AnalysisManager(engine_manager) 