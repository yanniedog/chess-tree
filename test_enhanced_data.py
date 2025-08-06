#!/usr/bin/env python3
"""
Test script for enhanced data manager
Verifies automatic dataset downloading and position-specific data retrieval
"""
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_manager import DataManager
from utils import get_logger

logger = get_logger(__name__)

def test_enhanced_data_manager():
    """Test the enhanced data manager functionality"""
    print("=== Testing Enhanced Data Manager ===")
    
    try:
        # Initialize data manager
        print("Initializing data manager...")
        data_manager = DataManager()
        
        # Test position (starting position after 1. d4)
        test_fen = "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1"
        print(f"Testing position: {test_fen}")
        
        # Get position stats (this should trigger automatic dataset download)
        print("Getting position statistics...")
        start_time = time.time()
        stats = data_manager.get_position_stats(test_fen)
        end_time = time.time()
        
        print(f"Retrieved {len(stats)} moves in {end_time - start_time:.2f} seconds")
        
        if stats:
            print("\nTop moves:")
            for i, stat in enumerate(stats[:5]):
                print(f"{i+1}. {stat.move}: {stat.performance_score:.3f} "
                      f"({stat.wins}W/{stat.losses}L/{stat.draws}D) "
                      f"Confidence: {stat.confidence_level}")
        else:
            print("No statistics found")
        
        # Test another position (middlegame)
        test_fen2 = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        print(f"\nTesting middlegame position: {test_fen2}")
        
        stats2 = data_manager.get_position_stats(test_fen2)
        print(f"Retrieved {len(stats2)} moves for middlegame position")
        
        if stats2:
            print("\nTop moves (middlegame):")
            for i, stat in enumerate(stats2[:5]):
                print(f"{i+1}. {stat.move}: {stat.performance_score:.3f} "
                      f"({stat.wins}W/{stat.losses}L/{stat.draws}D) "
                      f"Confidence: {stat.confidence_level}")
        
        print("\n=== Test completed successfully ===")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        logger.error(f"Test failed: {e}")
        return False

def test_dataset_availability():
    """Test dataset availability and download functionality"""
    print("\n=== Testing Dataset Availability ===")
    
    try:
        data_manager = DataManager()
        
        # Check available datasets
        print("Checking available datasets...")
        for dataset_name in data_manager.dataset_manager.dataset_sources:
            is_available = data_manager.dataset_manager.is_dataset_available(dataset_name)
            status = "✓ Available" if is_available else "✗ Not available"
            print(f"  {dataset_name}: {status}")
        
        # Test dataset download
        print("\nTesting dataset download...")
        success = data_manager.download_dataset("lichess_2023_01")
        print(f"Download result: {'✓ Success' if success else '✗ Failed'}")
        
        return True
        
    except Exception as e:
        print(f"Error testing dataset availability: {e}")
        logger.error(f"Dataset availability test failed: {e}")
        return False

if __name__ == "__main__":
    print("Enhanced Data Manager Test")
    print("=" * 40)
    
    # Run tests
    test1_success = test_enhanced_data_manager()
    test2_success = test_dataset_availability()
    
    if test1_success and test2_success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1) 