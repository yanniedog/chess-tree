#!/usr/bin/env python3
"""
Dataset monitoring script for continuous dataset access health monitoring
"""
import sys
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from utils import get_logger
from data_manager import DataManager, DatasetManager

logger = get_logger(__name__)

@dataclass
class DatasetHealth:
    """Dataset health information"""
    name: str
    status: str  # "healthy", "warning", "error", "unknown"
    last_check: datetime
    last_access: Optional[datetime] = None
    access_count: int = 0
    error_count: int = 0
    download_attempts: int = 0
    file_size_mb: float = 0.0
    checksum: Optional[str] = None
    error_message: Optional[str] = None

class DatasetMonitor:
    """Continuous dataset health monitoring"""
    
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self.data_manager = DataManager()
        self.dataset_manager = self.data_manager.dataset_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.health_data = {}
        self.lock = threading.Lock()
        self.monitor_thread = None
        
        # Initialize health data for all datasets
        for dataset_name in self.dataset_manager.dataset_sources:
            self.health_data[dataset_name] = DatasetHealth(
                name=dataset_name,
                status="unknown",
                last_check=datetime.now()
            )
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        if self.monitoring:
            logger.warning("Monitoring already running")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started dataset monitoring (check interval: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped dataset monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._check_all_datasets()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_all_datasets(self):
        """Check health of all datasets"""
        logger.debug("Checking dataset health...")
        
        for dataset_name in self.dataset_manager.dataset_sources:
            try:
                self._check_dataset_health(dataset_name)
            except Exception as e:
                logger.error(f"Error checking health of {dataset_name}: {e}")
                self._update_health(dataset_name, "error", error_message=str(e))
    
    def _check_dataset_health(self, dataset_name: str):
        """Check health of a specific dataset"""
        with self.lock:
            health = self.health_data[dataset_name]
            health.last_check = datetime.now()
        
        try:
            # Get dataset status
            status_info = self.dataset_manager.get_dataset_status(dataset_name)
            
            # Check if dataset is available and verified
            is_available = self.dataset_manager.is_dataset_available(dataset_name)
            
            if is_available:
                # Dataset is healthy
                self._update_health(dataset_name, "healthy", 
                                  file_size_mb=status_info.get("file_size_mb", 0),
                                  checksum=status_info.get("checksum"))
                logger.debug(f"Dataset {dataset_name} is healthy")
            else:
                # Dataset is not available
                if status_info.get("downloaded", False):
                    # Downloaded but not verified (corrupted)
                    self._update_health(dataset_name, "warning", 
                                      error_message="Dataset downloaded but failed verification")
                    logger.warning(f"Dataset {dataset_name} is corrupted")
                else:
                    # Not downloaded
                    self._update_health(dataset_name, "error", 
                                      error_message="Dataset not downloaded")
                    logger.debug(f"Dataset {dataset_name} is not downloaded")
                    
        except Exception as e:
            self._update_health(dataset_name, "error", error_message=str(e))
            logger.error(f"Error checking health of {dataset_name}: {e}")
    
    def _update_health(self, dataset_name: str, status: str, **kwargs):
        """Update health data for a dataset"""
        with self.lock:
            if dataset_name in self.health_data:
                health = self.health_data[dataset_name]
                health.status = status
                health.last_check = datetime.now()
                
                for key, value in kwargs.items():
                    if hasattr(health, key):
                        setattr(health, key, value)
    
    def record_access(self, dataset_name: str, success: bool = True):
        """Record dataset access attempt"""
        with self.lock:
            if dataset_name in self.health_data:
                health = self.health_data[dataset_name]
                health.last_access = datetime.now()
                health.access_count += 1
                
                if not success:
                    health.error_count += 1
    
    def record_download_attempt(self, dataset_name: str):
        """Record download attempt"""
        with self.lock:
            if dataset_name in self.health_data:
                health = self.health_data[dataset_name]
                health.download_attempts += 1
    
    def get_health_summary(self) -> Dict:
        """Get summary of dataset health"""
        with self.lock:
            summary = {
                "total_datasets": len(self.health_data),
                "healthy": 0,
                "warning": 0,
                "error": 0,
                "unknown": 0,
                "datasets": {}
            }
            
            for name, health in self.health_data.items():
                summary["datasets"][name] = {
                    "status": health.status,
                    "last_check": health.last_check.isoformat(),
                    "last_access": health.last_access.isoformat() if health.last_access else None,
                    "access_count": health.access_count,
                    "error_count": health.error_count,
                    "download_attempts": health.download_attempts,
                    "file_size_mb": health.file_size_mb,
                    "checksum": health.checksum,
                    "error_message": health.error_message
                }
                
                summary[health.status] += 1
            
            return summary
    
    def get_unhealthy_datasets(self) -> List[str]:
        """Get list of unhealthy datasets"""
        with self.lock:
            unhealthy = []
            for name, health in self.health_data.items():
                if health.status in ["warning", "error"]:
                    unhealthy.append(name)
            return unhealthy
    
    def get_dataset_recommendations(self) -> List[str]:
        """Get recommendations for dataset issues"""
        recommendations = []
        
        with self.lock:
            for name, health in self.health_data.items():
                if health.status == "error":
                    if health.error_count > 5:
                        recommendations.append(f"Dataset {name} has {health.error_count} errors - consider re-downloading")
                    elif not health.last_access:
                        recommendations.append(f"Dataset {name} has never been accessed - consider downloading if needed")
                elif health.status == "warning":
                    recommendations.append(f"Dataset {name} is corrupted - consider re-downloading")
        
        return recommendations

def main():
    """Main function for dataset monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dataset monitoring tool")
    parser.add_argument("--interval", "-i", type=int, default=300,
                       help="Check interval in seconds (default: 300)")
    parser.add_argument("--duration", "-d", type=int, default=0,
                       help="Monitoring duration in seconds (0 = run indefinitely)")
    parser.add_argument("--summary", "-s", action="store_true",
                       help="Show health summary and exit")
    parser.add_argument("--recommendations", "-r", action="store_true",
                       help="Show recommendations and exit")
    
    args = parser.parse_args()
    
    try:
        monitor = DatasetMonitor(check_interval=args.interval)
        
        if args.summary:
            # Show current health summary
            summary = monitor.get_health_summary()
            logger.info("Dataset Health Summary:")
            logger.info(f"Total datasets: {summary['total_datasets']}")
            logger.info(f"Healthy: {summary['healthy']}")
            logger.info(f"Warning: {summary['warning']}")
            logger.info(f"Error: {summary['error']}")
            logger.info(f"Unknown: {summary['unknown']}")
            
            unhealthy = monitor.get_unhealthy_datasets()
            if unhealthy:
                logger.warning(f"Unhealthy datasets: {', '.join(unhealthy)}")
            
            return 0
        
        if args.recommendations:
            # Show recommendations
            recommendations = monitor.get_dataset_recommendations()
            if recommendations:
                logger.info("Dataset Recommendations:")
                for rec in recommendations:
                    logger.info(f"  - {rec}")
            else:
                logger.info("No recommendations at this time")
            
            return 0
        
        # Start monitoring
        logger.info("Starting dataset monitoring...")
        monitor.start_monitoring()
        
        try:
            if args.duration > 0:
                logger.info(f"Monitoring for {args.duration} seconds...")
                time.sleep(args.duration)
            else:
                logger.info("Monitoring indefinitely (press Ctrl+C to stop)...")
                while True:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        
        finally:
            monitor.stop_monitoring()
            
            # Show final summary
            summary = monitor.get_health_summary()
            logger.info("\nFinal Dataset Health Summary:")
            logger.info(f"Total datasets: {summary['total_datasets']}")
            logger.info(f"Healthy: {summary['healthy']}")
            logger.info(f"Warning: {summary['warning']}")
            logger.info(f"Error: {summary['error']}")
            logger.info(f"Unknown: {summary['unknown']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in dataset monitoring: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 