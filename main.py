#!/usr/bin/env python3
"""
Main entry point for the Chess Opening Explorer
"""
import sys
import argparse
import logging
from pathlib import Path

from config import config
from utils import get_logger, set_log_level

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Chess Opening Explorer - AI-powered opening analysis tool"
    )
    
    parser.add_argument(
        '--mode',
        choices=['gui', 'api', 'data'],
        default='gui',
        help='Run mode: gui (default), api (REST server), or data (data processing)'
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='API server host (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='API server port (default: 5000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = get_logger()
    if args.debug:
        set_log_level(logging.DEBUG)
    
    logger.info("Starting Chess Opening Explorer")
    logger.info(f"Mode: {args.mode}")
    
    try:
        if args.mode == 'gui':
            # Import and run GUI immediately
            logger.info("Launching GUI application...")
            from gui import main as gui_main
            gui_main()
            
        elif args.mode == 'api':
            # Import and run API server
            from api_server import run_api_server
            run_api_server(host=args.host, port=args.port, debug=args.debug)
            
        elif args.mode == 'data':
            # Data processing mode
            from data_manager import DataManager
            data_manager = DataManager()
            
            # Example: process some data
            logger.info("Data processing mode - use this for batch operations")
            
            # You could add specific data processing commands here
            # For example:
            # - Update archive index
            # - Process specific archives
            # - Clean up cache
            # - Export statistics
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 