#!/usr/bin/env python3
"""
Test script for the modern GUI design
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from gui import MainWindow

def test_modern_gui():
    """Test the modern GUI design"""
    app = QApplication(sys.argv)
    
    # Set modern application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    print("✅ Modern GUI launched successfully!")
    print("🎨 Features of the new design:")
    print("   - Modern color scheme with professional styling")
    print("   - Enhanced chess board with hover effects")
    print("   - Improved button styling with hover states")
    print("   - Better typography and spacing")
    print("   - Responsive layout with proper margins")
    print("   - Color-coded confidence levels in stats table")
    print("   - Modern group boxes and controls")
    
    # Start the application
    sys.exit(app.exec())

if __name__ == "__main__":
    test_modern_gui() 