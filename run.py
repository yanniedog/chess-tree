#!/usr/bin/env python3
"""
Simple run script for the Chess Opening Explorer
"""
import sys
import os
from utils import get_logger, set_log_level
import logging

logger = get_logger()

def show_help():
    """Show help information"""
    logger.info("Showing help information")
    help_text = """Chess Opening Explorer - AI-powered opening analysis tool

Usage:
  python run.py [command]

Commands:
  gui          - Launch the GUI application
  api          - Start the REST API server
  test         - Run system tests
  demo         - Run the demo script
  dataset-test - Run comprehensive dataset access reliability tests
  help         - Show this help message

Examples:
  python run.py gui
  python run.py api --host 0.0.0.0 --port 5000
  python run.py test
  python run.py dataset-test"""
    
    logger.info(help_text)
    print(help_text)

def main():
    """Main entry point"""
    try:
        if len(sys.argv) < 2:
            logger.info("No command provided. Defaulting to GUI mode.")
            os.system("python main.py --mode gui")
            return 0
        command = sys.argv[1].lower()
        logger.info(f"Received command: {command}")
        if command == "help":
            show_help()
            return 0
        elif command == "gui":
            logger.info("Starting GUI...")
            os.system("python main.py --mode gui")
        elif command == "api":
            host = "localhost"
            port = "5000"
            # Parse additional arguments
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--host" and i + 1 < len(sys.argv):
                    host = sys.argv[i + 1]
                elif arg == "--port" and i + 1 < len(sys.argv):
                    port = sys.argv[i + 1]
            logger.info(f"Starting API server on {host}:{port}...")
            os.system(f"python main.py --mode api --host {host} --port {port}")
        elif command == "test":
            logger.info("Running system tests...")
            os.system("python test_system.py")
        elif command == "demo":
            logger.info("Running demo...")
            os.system("python demo.py")
        elif command == "dataset-test":
            logger.info("Running comprehensive dataset access reliability tests...")
            os.system("python test_dataset_access.py")
        else:
            logger.error(f"Unknown command: {command}")
            show_help()
            return 1
        return 0
    except Exception as e:
        logger.error(f"Fatal error in run.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main()) 