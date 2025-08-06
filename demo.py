#!/usr/bin/env python3
"""
Demo script for the Chess Opening Explorer
"""
import sys
import logging
from pathlib import Path

from config import config
from data_manager import DataManager
from engine_analyzer import engine_manager
from utils import normalize_fen, get_legal_moves, get_logger, fetch_lichess_api

logger = get_logger()

def demo_basic_functionality():
    """Demonstrate basic functionality"""
    demo_text = "=== Chess Opening Explorer Demo ===\n"
    logger.info(demo_text)
    print(demo_text)
    
    # Initialize data manager
    init_text = "1. Initializing data manager..."
    logger.info(init_text)
    print(init_text)
    data_manager = DataManager()
    success_text = "   ✓ Data manager initialized\n"
    logger.info(success_text)
    print(success_text)
    
    # Test with starting position
    test_text = "2. Testing with starting position..."
    logger.info(test_text)
    print(test_text)
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    normalized_fen = normalize_fen(fen)
    fen_info = f"   Original FEN: {fen}"
    logger.info(fen_info)
    print(fen_info)
    norm_info = f"   Normalized FEN: {normalized_fen}"
    logger.info(norm_info)
    print(norm_info)
    
    # Get legal moves
    legal_moves = get_legal_moves(fen)
    moves_info = f"   Legal moves: {len(legal_moves)}"
    logger.info(moves_info)
    print(moves_info)
    first_moves = f"   First 5 moves: {legal_moves[:5]}"
    logger.info(first_moves)
    print(first_moves)
    
    # Get statistics (will be empty initially)
    stats = data_manager.get_position_stats(fen)
    stats_info = f"   Statistics found: {len(stats)} moves with data"
    logger.info(stats_info)
    print(stats_info)
    logger.info("")
    print()
    
    # Test engine availability
    print("3. Checking engine availability...")
    engines = engine_manager.get_available_engines()
    if engines:
        print(f"   ✓ Available engines: {engines}")
        # Test engine analysis
        try:
            moves = engine_manager.analyze_position(fen, "stockfish", time_limit=1000)
            print(f"   ✓ Engine analysis: {len(moves)} moves analyzed")
            if moves:
                print(f"   Top move: {moves[0].move} (score: {moves[0].score})")
        except Exception as e:
            print(f"   ⚠ Engine analysis failed: {e}")
    else:
        print("   ⚠ No engines available (Stockfish not installed)")
    print()
    
    # Test API functionality
    print("4. Testing API functionality...")
    try:
        from api_server import app
        with app.test_client() as client:
            response = client.get('/api/health')
            print(f"   ✓ API health check: {response.status_code}")
            
            response = client.get(f'/api/position/{fen.replace(" ", "%20")}')
            print(f"   ✓ Position info: {response.status_code}")
    except Exception as e:
        print(f"   ⚠ API test failed: {e}")
    print()
    
    # Show configuration
    print("5. System configuration...")
    print(f"   Cache directory: {config.cache.cache_dir}")
    print(f"   Board size: {config.ui.board_size}")
    print(f"   Max cache size: {config.cache.max_size_gb} GB")
    print(f"   Network timeout: {config.network.timeout_seconds} seconds")
    print()
    
    # Get Lichess stats for the starting position
    print("   Fetching Lichess stats for starting position...")
    try:
        lichess_stats = fetch_lichess_api(fen, endpoint="lichess")
        print(f"   ✓ Lichess stats: {lichess_stats}")
    except Exception as e:
        print(f"   ⚠ Failed to fetch Lichess stats: {e}")
    print()
    # Get Lichess cloud eval for the starting position
    print("   Fetching Lichess cloud evaluation for starting position...")
    try:
        lichess_eval = fetch_lichess_api(fen, endpoint="cloud-eval")
        print(f"   ✓ Lichess cloud eval: {lichess_eval}")
    except Exception as e:
        print(f"   ⚠ Failed to fetch Lichess cloud eval: {e}")
    print()
    
    print("=== Demo Complete ===")
    print("\nTo run the full application:")
    print("  GUI mode: python main.py")
    print("  API mode: python main.py --mode api")
    print("  Debug mode: python main.py --debug")

def demo_advanced_features():
    """Demonstrate advanced features"""
    print("\n=== Advanced Features Demo ===\n")
    
    # Test different positions
    positions = [
        ("Starting position", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("After 1.e4", "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"),
        ("Sicilian Defense", "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"),
    ]
    
    data_manager = DataManager()
    
    for name, fen in positions:
        print(f"Position: {name}")
        normalized = normalize_fen(fen)
        moves = get_legal_moves(fen)
        stats = data_manager.get_position_stats(fen)
        
        print(f"  Legal moves: {len(moves)}")
        print(f"  Stats available: {len(stats)}")
        print(f"  Normalized FEN: {normalized[:50]}...")
        print()

def main():
    """Main demo function"""
    try:
        demo_basic_functionality()
        demo_advanced_features()
        
        print("\n🎉 Demo completed successfully!")
        print("\nThe Chess Opening Explorer is ready to use.")
        print("Key features:")
        print("  • Real-time performance analysis")
        print("  • Multiple analysis modes")
        print("  • Network version filtering")
        print("  • Engine integration")
        print("  • REST API access")
        print("  • Persistent caching")
        print("  • FEN normalization")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 