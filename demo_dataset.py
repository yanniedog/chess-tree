#!/usr/bin/env python3
"""
Demo script showing the dataset analyzer functionality
"""
import chess
import time
from dataset_analyzer import dataset_analyzer
from utils import get_logger

logger = get_logger()

def demo_dataset_analyzer():
    """Demo the dataset analyzer functionality"""
    
    print("Chess Dataset Analyzer Demo")
    print("=" * 50)
    print("This demo shows how the program now uses local datasets instead of Stockfish")
    print()
    
    # Test a common opening position
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"  # After e4
    board = chess.Board(fen)
    
    print(f"Analyzing position: {board.fen()}")
    print(f"Position: After 1. e4")
    print()
    
    # Get analysis from dataset
    moves = dataset_analyzer.analyze_position(fen)
    
    if moves:
        print(f"Found {len(moves)} moves from dataset analysis:")
        print("-" * 60)
        print(f"{'Move':<8} {'Wins':<6} {'Losses':<8} {'Draws':<6} {'Total':<6} {'Perf':<6} {'Eval':<6}")
        print("-" * 60)
        
        for i, move in enumerate(moves[:10], 1):  # Show top 10 moves
            san = board.san(chess.Move.from_uci(move.move))
            print(f"{san:<8} {move.wins:<6} {move.losses:<8} {move.draws:<6} "
                  f"{move.total_games:<6} {move.performance_score:.3f} {move.evaluation_score:+4d}")
        
        print("-" * 60)
        print()
        
        # Show best move
        best_move = moves[0]
        best_san = board.san(chess.Move.from_uci(best_move.move))
        print(f"Best move: {best_san}")
        print(f"Performance: {best_move.performance_score:.3f}")
        print(f"Evaluation: {best_move.evaluation_score:+d} centipawns")
        print(f"Confidence: {best_move.confidence_level}")
        print(f"Games analyzed: {best_move.total_games}")
        
    else:
        print("No moves found in dataset")
    
    print()
    print("Dataset Information:")
    print("-" * 30)
    available_datasets = dataset_analyzer.get_available_datasets()
    if available_datasets:
        print(f"Available datasets: {', '.join(available_datasets)}")
        for dataset in available_datasets:
            info = dataset_analyzer.get_dataset_info(dataset)
            print(f"  {dataset}: {info.get('description', 'N/A')}")
    else:
        print("No datasets downloaded yet")
        print("Available for download:")
        for name, source in dataset_analyzer.downloader.dataset_sources.items():
            print(f"  {name}: {source['description']} ({source['size_mb']}MB)")
    
    print()
    print("Key Benefits:")
    print("- No need for Stockfish installation")
    print("- Analysis based on real game data")
    print("- Fast local analysis")
    print("- Can work offline once datasets are downloaded")
    print("- Provides statistical insights from actual games")

if __name__ == "__main__":
    demo_dataset_analyzer() 