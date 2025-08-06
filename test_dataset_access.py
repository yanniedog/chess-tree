#!/usr/bin/env python3
"""
Comprehensive test script for dataset access reliability
"""
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from utils import get_logger
from data_manager import DataManager, DatasetManager

logger = get_logger(__name__)

class DatasetAccessTester:
    """Test dataset access reliability"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.dataset_manager = self.data_manager.dataset_manager
        self.test_results = {}
        
    def test_dataset_integrity(self) -> bool:
        """Test dataset file integrity"""
        logger.info("=== Testing Dataset Integrity ===")
        
        try:
            all_passed = True
            
            for dataset_name in self.dataset_manager.dataset_sources:
                logger.info(f"Testing integrity of {dataset_name}...")
                
                # Check if dataset exists
                is_available = self.dataset_manager.is_dataset_available(dataset_name)
                status = "✓ Available and verified" if is_available else "✗ Not available or corrupted"
                logger.info(f"  {dataset_name}: {status}")
                
                if not is_available:
                    all_passed = False
                    
                    # Try to download if not available
                    logger.info(f"  Attempting to download {dataset_name}...")
                    success = self.dataset_manager.download_dataset(dataset_name)
                    if success:
                        logger.info(f"  ✓ Successfully downloaded {dataset_name}")
                        all_passed = True
                    else:
                        logger.error(f"  ✗ Failed to download {dataset_name}")
                
                # Get detailed status
                status_info = self.dataset_manager.get_dataset_status(dataset_name)
                logger.info(f"  Status: {status_info}")
                
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing dataset integrity: {e}")
            return False
    
    def test_dataset_download_reliability(self) -> bool:
        """Test dataset download reliability with retries"""
        logger.info("=== Testing Dataset Download Reliability ===")
        
        try:
            all_passed = True
            
            # Test download of a dataset that might not exist
            test_dataset = "lichess_2023_01"
            
            logger.info(f"Testing download reliability for {test_dataset}...")
            
            # Check current status
            initial_status = self.dataset_manager.get_dataset_status(test_dataset)
            logger.info(f"Initial status: {initial_status}")
            
            # Attempt download
            success = self.dataset_manager.download_dataset(test_dataset)
            
            if success:
                logger.info(f"✓ Successfully downloaded {test_dataset}")
                
                # Verify the download
                final_status = self.dataset_manager.get_dataset_status(test_dataset)
                logger.info(f"Final status: {final_status}")
                
                if final_status.get("verified", False):
                    logger.info("✓ Download verification passed")
                else:
                    logger.error("✗ Download verification failed")
                    all_passed = False
            else:
                logger.warning(f"⚠ Download failed for {test_dataset} (this may be expected if already exists)")
                
                # Check if it's already available
                if self.dataset_manager.is_dataset_available(test_dataset):
                    logger.info("✓ Dataset is already available")
                else:
                    logger.error("✗ Dataset is not available and download failed")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing dataset download reliability: {e}")
            return False
    
    def test_position_data_access(self) -> bool:
        """Test position data access with various positions"""
        logger.info("=== Testing Position Data Access ===")
        
        try:
            all_passed = True
            
            # Test positions
            test_positions = [
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
                "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",  # After e4
                "rnbqkbnr/pp1ppppp/2p5/4P3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",  # After e4 c6
            ]
            
            for i, fen in enumerate(test_positions, 1):
                logger.info(f"Testing position {i}: {fen[:50]}...")
                
                try:
                    # Get position stats
                    stats = self.data_manager.get_position_stats(fen)
                    
                    if stats:
                        logger.info(f"  ✓ Found {len(stats)} moves for position {i}")
                        
                        # Check if stats are valid
                        for stat in stats[:3]:  # Check first 3 moves
                            if not hasattr(stat, 'total_games') or stat.total_games < 0:
                                logger.warning(f"  ⚠ Invalid stats for move {stat.move}")
                                all_passed = False
                    else:
                        logger.warning(f"  ⚠ No stats found for position {i} (using sample data)")
                        
                except Exception as e:
                    logger.error(f"  ✗ Error accessing position {i}: {e}")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing position data access: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling for various failure scenarios"""
        logger.info("=== Testing Error Handling ===")
        
        try:
            all_passed = True
            
            # Test with invalid FEN
            invalid_fen = "invalid_fen_string"
            logger.info("Testing with invalid FEN...")
            
            try:
                stats = self.data_manager.get_position_stats(invalid_fen)
                logger.info("  ✓ Handled invalid FEN gracefully")
            except Exception as e:
                logger.error(f"  ✗ Failed to handle invalid FEN: {e}")
                all_passed = False
            
            # Test with non-existent dataset
            logger.info("Testing with non-existent dataset...")
            
            try:
                success = self.dataset_manager.download_dataset("non_existent_dataset")
                if not success:
                    logger.info("  ✓ Correctly handled non-existent dataset")
                else:
                    logger.error("  ✗ Should have failed for non-existent dataset")
                    all_passed = False
            except Exception as e:
                logger.info(f"  ✓ Handled non-existent dataset error: {e}")
            
            # Test dataset status for non-existent dataset
            try:
                status = self.dataset_manager.get_dataset_status("non_existent_dataset")
                if "error" in status:
                    logger.info("  ✓ Correctly returned error for non-existent dataset")
                else:
                    logger.error("  ✗ Should have returned error for non-existent dataset")
                    all_passed = False
            except Exception as e:
                logger.error(f"  ✗ Error getting status for non-existent dataset: {e}")
                all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing error handling: {e}")
            return False
    
    def test_cache_reliability(self) -> bool:
        """Test cache reliability and consistency"""
        logger.info("=== Testing Cache Reliability ===")
        
        try:
            all_passed = True
            
            # Test position
            test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            logger.info("Testing cache consistency...")
            
            # Get stats multiple times
            stats1 = self.data_manager.get_position_stats(test_fen)
            time.sleep(0.1)  # Small delay
            stats2 = self.data_manager.get_position_stats(test_fen)
            
            if len(stats1) == len(stats2):
                logger.info(f"  ✓ Cache consistency: {len(stats1)} moves returned consistently")
            else:
                logger.warning(f"  ⚠ Cache inconsistency: {len(stats1)} vs {len(stats2)} moves")
                all_passed = False
            
            # Test cache with different networks
            logger.info("Testing cache with different networks...")
            
            stats_all = self.data_manager.get_position_stats(test_fen)
            stats_sample = self.data_manager.get_position_stats(test_fen, "sample")
            
            if stats_all or stats_sample:
                logger.info("  ✓ Cache works with different network filters")
            else:
                logger.warning("  ⚠ Cache may have issues with network filtering")
                all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing cache reliability: {e}")
            return False
    
    def test_dataset_cleanup(self) -> bool:
        """Test dataset cleanup functionality"""
        logger.info("=== Testing Dataset Cleanup ===")
        
        try:
            all_passed = True
            
            # Test cleanup
            logger.info("Testing dataset cleanup...")
            
            try:
                self.data_manager.cleanup_cache()
                logger.info("  ✓ Cache cleanup completed successfully")
            except Exception as e:
                logger.error(f"  ✗ Cache cleanup failed: {e}")
                all_passed = False
            
            # Test corrupted dataset cleanup
            logger.info("Testing corrupted dataset cleanup...")
            
            try:
                self.dataset_manager.cleanup_corrupted_datasets()
                logger.info("  ✓ Corrupted dataset cleanup completed successfully")
            except Exception as e:
                logger.error(f"  ✗ Corrupted dataset cleanup failed: {e}")
                all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error testing dataset cleanup: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all dataset access tests"""
        logger.info("Starting comprehensive dataset access reliability tests...")
        
        tests = [
            ("Dataset Integrity", self.test_dataset_integrity),
            ("Download Reliability", self.test_dataset_download_reliability),
            ("Position Data Access", self.test_position_data_access),
            ("Error Handling", self.test_error_handling),
            ("Cache Reliability", self.test_cache_reliability),
            ("Dataset Cleanup", self.test_dataset_cleanup),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} Test ---")
            try:
                result = test_func()
                results[test_name] = result
                status = "PASSED" if result else "FAILED"
                logger.info(f"✓ {test_name} test {status}")
            except Exception as e:
                logger.error(f"✗ {test_name} test failed with exception: {e}")
                results[test_name] = False
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        logger.info("\n" + "="*60)
        logger.info("DATASET ACCESS RELIABILITY TEST SUMMARY")
        logger.info("="*60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓ PASSED" if result else "✗ FAILED"
            logger.info(f"{test_name:.<40} {status}")
        
        logger.info("-" * 60)
        logger.info(f"Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All dataset access tests passed! Datasets are reliable.")
        else:
            logger.error("❌ Some dataset access tests failed. Please check the errors above.")
        
        return passed == total

def main():
    """Main test function"""
    try:
        tester = DatasetAccessTester()
        results = tester.run_all_tests()
        success = tester.print_summary(results)
        
        if success:
            logger.info("Dataset access reliability verification completed successfully!")
            return 0
        else:
            logger.error("Dataset access reliability verification failed!")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error during testing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 