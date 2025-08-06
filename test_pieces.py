#!/usr/bin/env python3
"""
Test script to verify improved chess piece outlines.
"""

import sys
import chess
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor

# Import the chess board widget from gui.py
from gui import ChessBoardWidget

class PieceTestWidget(QWidget):
    """Simple widget to test piece drawing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Piece Outline Test")
        self.setMinimumSize(400, 300)
        
        # Create a test board with all pieces
        self.board = chess.Board()
        self.board.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        
        # Create chess board widget
        self.chess_board = ChessBoardWidget()
        self.chess_board.set_fen(self.board.fen())
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Test of Improved Chess Piece Outlines"))
        layout.addWidget(self.chess_board)
        
        # Set zoom to see details better
        self.chess_board.set_zoom(150)  # 150% zoom

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    test_widget = PieceTestWidget()
    test_widget.show()
    
    print("Testing improved chess piece outlines...")
    print("You should see:")
    print("- Better contrast between piece colors and outlines")
    print("- More distinct piece shapes")
    print("- Clearer identification of each piece type")
    print("- Improved proportions and stability")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 