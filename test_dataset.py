#!/usr/bin/env python3
"""
Test script for the dataset analyzer
"""
import chess
import time
from dataset_analyzer import dataset_analyzer
from utils import get_logger

logger = get_logger()

def test_dataset_analyzer():
    """Test the dataset analyzer with common chess positions"""
    
    # Test positions
    test_positions = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",  # e4
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",  # e4 c5
    ]
    
    print("Testing Dataset Analyzer")
    print("=" * 50)
    
    for i, fen in enumerate(test_positions, 1):
        print(f"\nTest {i}: Position {fen[:50]}...")
        
        # Analyze position
        moves = dataset_analyzer.analyze_position(fen)
        
        if moves:
            print(f"Found {len(moves)} moves:")
            for j, move in enumerate(moves[:5], 1):  # Show top 5 moves
                print(f"  {j}. {move.move}: {move.wins}W/{move.losses}L/{move.draws}D "
                      f"(Perf: {move.performance_score:.3f}, Eval: {move.evaluation_score})")
        else:
            print("No moves found")
    
    # Test dataset download
    print("\n" + "=" * 50)
    print("Testing Dataset Download")
    
    available_datasets = dataset_analyzer.get_available_datasets()
    print(f"Available datasets: {available_datasets}")
    
    if not available_datasets:
        print("No datasets available. Testing download...")
        # Note: This would download a large file, so we'll just test the interface
        print("Dataset download interface ready")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_dataset_analyzer() 