#!/usr/bin/env python3
"""
Test script for the Chess Opening Explorer system
"""
import sys
import logging
from pathlib import Path

from utils import get_logger

# Configure logging
logger = get_logger()

def test_imports():
    """Test that all modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        import chess
        logger.info("✓ python-chess imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import python-chess: {e}")
        return False
    
    try:
        from PyQt6.QtWidgets import QApplication
        logger.info("✓ PyQt6 imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import PyQt6: {e}")
        return False
    
    try:
        import lmdb
        logger.info("✓ lmdb imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import lmdb: {e}")
        return False
    
    try:
        import requests
        logger.info("✓ requests imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import requests: {e}")
        return False
    
    try:
        from flask import Flask
        logger.info("✓ Flask imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import Flask: {e}")
        return False
    
    return True

def test_config():
    """Test configuration system"""
    logger.info("Testing configuration...")
    
    try:
        from config import config
        logger.info("✓ Configuration loaded successfully")
        logger.info(f"  Cache directory: {config.cache.cache_dir}")
        logger.info(f"  Board size: {config.ui.board_size}")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

def test_utils():
    """Test utility functions"""
    logger.info("Testing utilities...")
    
    try:
        from utils import normalize_fen, get_legal_moves, is_valid_fen
        from utils import MoveStats, GameResult
        
        # Test FEN normalization
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        normalized = normalize_fen(fen)
        logger.info(f"✓ FEN normalization: {normalized}")
        
        # Test legal moves
        moves = get_legal_moves(fen)
        logger.info(f"✓ Legal moves found: {len(moves)}")
        
        # Test FEN validation
        is_valid = is_valid_fen(fen)
        logger.info(f"✓ FEN validation: {is_valid}")
        
        # Test MoveStats
        stats = MoveStats(fen=fen, move="e2e4", wins=10, losses=5, draws=3)
        logger.info(f"✓ MoveStats created: performance={stats.performance_score:.3f}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Utilities test failed: {e}")
        return False

def test_data_manager():
    """Test data management system"""
    logger.info("Testing data manager...")
    
    try:
        from data_manager import DataManager
        
        # Initialize data manager
        data_manager = DataManager()
        logger.info("✓ DataManager initialized successfully")
        
        # Test getting position stats (will be empty initially)
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        stats = data_manager.get_position_stats(fen)
        logger.info(f"✓ Position stats retrieved: {len(stats)} moves")
        
        return True
    except Exception as e:
        logger.error(f"✗ Data manager test failed: {e}")
        return False

def test_engine_analyzer():
    """Test engine analysis system"""
    logger.info("Testing engine analyzer...")
    
    try:
        from engine_analyzer import engine_manager
        
        # Test engine availability
        engines = engine_manager.get_available_engines()
        logger.info(f"✓ Available engines: {engines}")
        
        if engines:
            # Test engine info
            engine_info = engine_manager.get_engine_info(engines[0])
            logger.info(f"✓ Engine info: {engine_info}")
        else:
            logger.warning("⚠ No engines available (Stockfish not installed)")
        
        return True
    except Exception as e:
        logger.error(f"✗ Engine analyzer test failed: {e}")
        return False

def test_gui_components():
    """Test GUI components (without starting full GUI)"""
    logger.info("Testing GUI components...")
    
    try:
        # Test that we can import GUI components
        from gui import ChessBoardWidget, StatsTable
        
        logger.info("✓ GUI components imported successfully")
        return True
    except Exception as e:
        logger.error(f"✗ GUI components test failed: {e}")
        return False

def test_api_server():
    """Test API server components"""
    logger.info("Testing API server...")
    
    try:
        from api_server import app
        
        # Test that Flask app can be created
        with app.test_client() as client:
            response = client.get('/api/health')
            logger.info(f"✓ API health check: {response.status_code}")
        
        return True
    except Exception as e:
        logger.error(f"✗ API server test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Chess Opening Explorer system tests...")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Utilities", test_utils),
        ("Data Manager", test_data_manager),
        ("Engine Analyzer", test_engine_analyzer),
        ("GUI Components", test_gui_components),
        ("API Server", test_api_server),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} test passed")
            else:
                logger.error(f"✗ {test_name} test failed")
        except Exception as e:
            logger.error(f"✗ {test_name} test failed with exception: {e}")
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready to use.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 