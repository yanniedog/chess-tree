import sys
import json
import time
import requests
from typing import List
from pathlib import Path

import chess
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

# Local imports
from config import config  # noqa: F401 – used elsewhere in project
from data_manager import DataManager  # noqa: F401 – used elsewhere in project
from dataset_analyzer import dataset_analyzer  # noqa: F401 – used elsewhere in project
from utils import (
    get_logger,
    normalize_fen,
    get_legal_moves,
    get_confidence_color,
    format_time,
    format_size,
    fetch_lichess_api,
)

# Ensure logger is initialized
logger = get_logger()


# ---------------------------------------------------------------------------
#                     HELPER  – THEME & FONT MIX‑IN
# ---------------------------------------------------------------------------
class ThemeMixin:
    """Centralise colour palette / font sizes so the whole GUI scales nicely."""

    def _init_theme(self):
        self.colours = {
            "light_square": QColor(128, 128, 128),  # 50% grey
            "dark_square": QColor(173, 216, 230),   # Pale blue
            "selected": QColor(255, 255, 0, 180),
            "legal_move": QColor(144, 238, 144, 180),
            "hover": QColor(0, 255, 0, 64),  # 25% opacity green
            "border": QColor(139, 69, 19),
            "text": QColor(220, 220, 220),
        }
        # Base font size auto‑scaled via ``self.font_scale`` (set by zoom slider)
        self.font_scale = 1.0

    # ------------------------------------------------------------------
    #  Convenience helpers so descendant widgets can grab scaled fonts.
    # ------------------------------------------------------------------
    def _font(self, pt_size: int, weight=QFont.Weight.Normal) -> QFont:
        f = QFont("Arial", max(6, round(pt_size * self.font_scale)))
        f.setWeight(weight)
        return f


# ---------------------------------------------------------------------------
#                                CHESS BOARD
# ---------------------------------------------------------------------------
class ChessBoardWidget(QWidget, ThemeMixin):
    """Interactive chess board that auto‑scales & supports zoom."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_theme()

        self.board = chess.Board()
        self.selected_square: int | None = None
        self.hover_square: int | None = None
        self.legal_moves: list[int] = []
        self.dragging = False
        self.drag_start_pos = None

        self.square_size_px = 64  # will be overridden in paintEvent
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.move_callback = None  # set by parent
        
        # Load chess piece images
        self.piece_images = {}
        self._load_piece_images()
        
        # Highlighting state for table hover
        self.highlighted_square = None
        self.highlighted_path = set()  # Set of squares in the move path

    def _load_piece_images(self):
        """Load chess piece images from Wikipedia URLs."""
        piece_urls = {
            # White pieces
            'K': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Chess_klt45.svg/75px-Chess_klt45.svg.png',
            'Q': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Chess_qlt45.svg/75px-Chess_qlt45.svg.png',
            'R': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Chess_rlt45.svg/75px-Chess_rlt45.svg.png',
            'B': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Chess_blt45.svg/75px-Chess_blt45.svg.png',
            'N': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Chess_nlt45.svg/75px-Chess_nlt45.svg.png',
            'P': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Chess_plt45.svg/75px-Chess_plt45.svg.png',
            # Black pieces
            'k': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Chess_kdt45.svg/75px-Chess_kdt45.svg.png',
            'q': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Chess_qdt45.svg/75px-Chess_qdt45.svg.png',
            'r': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Chess_rdt45.svg/75px-Chess_rdt45.svg.png',
            'b': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Chess_bdt45.svg/75px-Chess_bdt45.svg.png',
            'n': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Chess_ndt45.svg/75px-Chess_ndt45.svg.png',
            'p': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Chess_pdt45.svg/75px-Chess_pdt45.svg.png',
        }
        
        # Create cache directory if it doesn't exist
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        
        for piece_symbol, url in piece_urls.items():
            # Use descriptive filenames: white_king.png, black_queen.png, etc.
            piece_type = piece_symbol.upper()
            color = "white" if piece_symbol.isupper() else "black"
            cache_file = cache_dir / f"{color}_{piece_type.lower()}.png"
            
            # Load from cache if available, otherwise download
            if cache_file.exists():
                try:
                    pixmap = QPixmap(str(cache_file))
                    if not pixmap.isNull():
                        self.piece_images[piece_symbol] = pixmap
                        continue
                except Exception as e:
                    logger.warning(f"Failed to load cached piece {piece_symbol}: {e}")
            
            # Download image
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Save to cache
                with open(cache_file, 'wb') as f:
                    f.write(response.content)
                
                # Load pixmap
                pixmap = QPixmap()
                if pixmap.loadFromData(response.content):
                    self.piece_images[piece_symbol] = pixmap
                    logger.info(f"Successfully loaded piece {piece_symbol}")
                else:
                    logger.error(f"Failed to load piece image for {piece_symbol}")
                    
            except Exception as e:
                logger.error(f"Failed to download piece {piece_symbol} from {url}: {e}")

    # ----------------------------- PUBLIC API ----------------------------
    def set_zoom(self, percentage: int):
        """Zoom level coming from MainWindow toolbar (50–200 %)."""
        self.font_scale = percentage / 100.0
        # Square size roughly doubles with zoom but cap extremes.
        self.square_size_px = max(24, min(128, int(64 * self.font_scale)))
        self.update()

    def get_fen(self) -> str:
        return self.board.fen()

    def set_fen(self, fen: str):
        try:
            self.board = chess.Board(fen)
            self.selected_square = None
            self.update()
        except Exception as exc:  # pragma: no‑cover – defensive
            logger.error("Bad FEN supplied to board: %s", exc)

    def push_move(self, move: chess.Move):
        self.board.push(move)
        # Fetch Lichess stats for the new FEN after the move
        fen = normalize_fen(self.board.fen())
        logger = get_logger()
        try:
            lichess_data = fetch_lichess_api(fen, endpoint="lichess")
            logger.info(f"Fetched Lichess stats for FEN {fen}: {lichess_data}")
            # Optionally, store or display lichess_data here
            self.last_lichess_data = lichess_data
        except Exception as e:
            logger.error(f"Failed to fetch Lichess stats for FEN {fen}: {e}")
        if self.move_callback:
            self.move_callback()
        self.update()

    # --------------------------- PAINT & EVENTS ---------------------------
    def paintEvent(self, _event):  # noqa: N802 – Qt signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Keep board square even if window stretched.
        size = min(self.width(), self.height())
        self.square_size_px = size // 8
        offset_x = (self.width() - size) // 2
        offset_y = (self.height() - size) // 2

        # Draw rank and file labels
        label_size = 20
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QPen(self.colours["text"]))

        # File labels (a-h) at bottom
        for file in range(8):
            x = offset_x + file * self.square_size_px + self.square_size_px // 2
            y = offset_y + 8 * self.square_size_px + label_size
            painter.drawText(x - 10, y, 20, label_size, Qt.AlignmentFlag.AlignCenter, chr(97 + file))

        # Rank labels (1-8) on left
        for rank in range(8):
            x = offset_x - label_size
            y = offset_y + (7 - rank) * self.square_size_px + self.square_size_px // 2
            painter.drawText(x, y - 10, label_size, 20, Qt.AlignmentFlag.AlignCenter, str(rank + 1))

        # Draw squares & pieces
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                x = offset_x + file * self.square_size_px
                y = offset_y + (7 - rank) * self.square_size_px

                # Background colour
                is_light = (rank + file) % 2 == 0
                bg = (
                    self.colours["light_square"] if is_light else self.colours["dark_square"]
                )
                if self.selected_square == square:
                    bg = self.colours["selected"]
                elif square in self.legal_moves:
                    bg = self.colours["legal_move"]
                elif square == self.hover_square:
                    bg = self.colours["hover"]
                elif square == self.highlighted_square:
                    bg = self.colours["selected"]  # Use selected color for table hover highlight
                elif square in self.highlighted_path:
                    bg = self.colours["legal_move"]  # Use legal move color for path highlighting
                painter.fillRect(x, y, self.square_size_px, self.square_size_px, bg)

                # Piece
                piece = self.board.piece_at(square)
                if piece:
                    piece_symbol = piece.symbol()
                    if piece_symbol in self.piece_images:
                        # Calculate piece dimensions - make pieces fit nicely in squares
                        piece_size = int(self.square_size_px * 0.8)
                        center_x = x + self.square_size_px // 2
                        center_y = y + self.square_size_px // 2
                        
                        # Draw the piece image
                        pixmap = self.piece_images[piece_symbol]
                        scaled_pixmap = pixmap.scaled(piece_size, piece_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        
                        # Center the piece in the square
                        piece_x = center_x - scaled_pixmap.width() // 2
                        piece_y = center_y - scaled_pixmap.height() // 2
                        
                        painter.drawPixmap(piece_x, piece_y, scaled_pixmap)
                    else:
                        # Fallback to custom drawing if image not available
                        if piece.color == chess.WHITE:
                            piece_color = QColor(255, 255, 255)  # Pure white
                        else:
                            piece_color = QColor(64, 64, 64)  # Solid dark gray
                        
                        piece_size = int(self.square_size_px * 0.8)
                        center_x = x + self.square_size_px // 2
                        center_y = y + self.square_size_px // 2
                        
                        self._draw_piece(painter, piece, center_x, center_y, piece_size, piece_color)

    def _draw_piece(self, painter, piece, center_x, center_y, size, color):
        """Draw custom chess pieces with improved outlines and distinct shapes."""
        piece_type = piece.symbol().upper()
        
        # Create outline color - darker for white pieces, lighter for black pieces
        if piece.color == chess.WHITE:
            outline_color = QColor(64, 64, 64)  # Dark gray outline for white pieces
        else:
            outline_color = QColor(200, 200, 200)  # Light gray outline for black pieces
        
        # Set up painter with outline
        painter.setPen(QPen(outline_color, 2))  # Thicker outline for better visibility
        painter.setBrush(color)
        
        if piece_type == "P":  # Pawn
            self._draw_pawn(painter, center_x, center_y, size)
        elif piece_type == "R":  # Rook
            self._draw_rook(painter, center_x, center_y, size)
        elif piece_type == "N":  # Knight
            self._draw_knight(painter, center_x, center_y, size)
        elif piece_type == "B":  # Bishop
            self._draw_bishop(painter, center_x, center_y, size)
        elif piece_type == "Q":  # Queen
            self._draw_queen(painter, center_x, center_y, size)
        elif piece_type == "K":  # King
            self._draw_king(painter, center_x, center_y, size)

    def _draw_pawn(self, painter, x, y, size):
        """Draw a distinct pawn shape with better proportions."""
        # Base - wider and more stable
        painter.drawEllipse(x - size//2, y + size//3, size, size//6)
        # Body - more rounded, classic pawn shape
        painter.drawEllipse(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Head - smaller and more proportional
        painter.drawEllipse(x - size//5, y - size//2, int(size//2.5), int(size//2.5))

    def _draw_rook(self, painter, x, y, size):
        """Draw a distinct rook shape with clear battlements."""
        # Base - wider for stability
        painter.drawRect(x - size//2, y + size//3, size, size//6)
        # Body - main tower structure
        painter.drawRect(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Battlements - more prominent and distinct
        battlement_width = size//6
        battlement_height = size//4
        for i in range(4):
            painter.drawRect(x - size//3 + i * battlement_width, y - size//2, battlement_width, battlement_height)

    def _draw_knight(self, painter, x, y, size):
        """Draw a distinct knight shape with horse-like features."""
        # Base - wider for stability
        painter.drawEllipse(x - size//2, y + size//3, size, size//6)
        # Body - main structure
        painter.drawEllipse(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Head - more horse-like with snout
        painter.drawEllipse(x - size//4, y - size//2, size//2, size//2)
        # Ear - more prominent and distinctive
        painter.drawEllipse(x + size//6, y - size//2, size//3, size//3)
        # Snout - adds horse character
        painter.drawEllipse(x - size//3, y - size//3, size//4, size//4)

    def _draw_bishop(self, painter, x, y, size):
        """Draw a distinct bishop shape with clear mitre and cross."""
        # Base - wider for stability
        painter.drawEllipse(x - size//2, y + size//3, size, size//6)
        # Body - main structure
        painter.drawEllipse(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Mitre (hat) - more prominent
        painter.drawRect(x - size//3, y - size//2, int(size//1.5), size//5)
        # Cross on mitre - more visible and centered
        painter.drawRect(x - size//6, y - size//2, size//3, size//5)
        # Vertical part of cross
        painter.drawRect(x - size//12, y - size//2, size//6, size//5)

    def _draw_queen(self, painter, x, y, size):
        """Draw a distinct queen shape with elaborate crown."""
        # Base - wider for stability
        painter.drawEllipse(x - size//2, y + size//3, size, size//6)
        # Body - main structure
        painter.drawEllipse(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Crown base
        painter.drawRect(x - size//3, y - size//2, int(size//1.5), size//6)
        # Crown points - more elaborate and distinct
        crown_points = 5
        point_width = size//8
        for i in range(crown_points):
            painter.drawRect(x - size//3 + i * point_width, y - size//2, point_width, size//4)

    def _draw_king(self, painter, x, y, size):
        """Draw a distinct king shape with prominent cross crown."""
        # Base - wider for stability
        painter.drawEllipse(x - size//2, y + size//3, size, size//6)
        # Body - main structure
        painter.drawEllipse(x - size//3, y - size//6, int(size//1.5), int(size//1.2))
        # Crown base
        painter.drawRect(x - size//3, y - size//2, int(size//1.5), size//6)
        # Cross on crown - more prominent and centered
        painter.drawRect(x - size//6, y - size//2, size//3, size//6)
        # Vertical part of cross - taller and more prominent
        painter.drawRect(x - size//12, y - size//2, size//6, size//6)

     # ----------------------------- MOUSE I/O -----------------------------
    def _square_at_pos(self, pos) -> int | None:
        size = min(self.width(), self.height())
        offset_x = (self.width() - size) // 2
        offset_y = (self.height() - size) // 2
        sx = int((pos.x() - offset_x) // self.square_size_px)
        sy = 7 - int((pos.y() - offset_y) // self.square_size_px)
        if 0 <= sx < 8 and 0 <= sy < 8:
            return chess.square(sx, sy)
        return None

    def mousePressEvent(self, event):  # noqa: N802 – Qt signature
        if event.button() != Qt.MouseButton.LeftButton:
            return
        sq = self._square_at_pos(event.position().toPoint())
        if sq is None:
            return
        if self.selected_square is None and self.board.piece_at(sq):
            self.selected_square = sq
            self.legal_moves = [m.to_square for m in self.board.legal_moves if m.from_square == sq]
        else:
            # Determine if this is a pawn promotion
            move = None
            piece = self.board.piece_at(self.selected_square)
            if piece and piece.piece_type == chess.PAWN:
                # White pawn promotes on rank 8 (rank 7 in 0-indexed), black on rank 1 (rank 0)
                to_rank = chess.square_rank(sq)
                if (piece.color == chess.WHITE and to_rank == 7) or (piece.color == chess.BLACK and to_rank == 0):
                    # Default to queen promotion
                    move = chess.Move(self.selected_square, sq, promotion=chess.QUEEN)
            if move is None:
                move = chess.Move(self.selected_square, sq)
            if move in self.board.legal_moves:
                self.push_move(move)
            self.selected_square = None
            self.legal_moves = []
        self.update()

    def mouseMoveEvent(self, event):  # noqa: N802 – Qt signature
        sq = self._square_at_pos(event.position().toPoint())
        self.hover_square = sq
        self.update()
    
    def highlight_move(self, square):
        """Highlight a square for table hover."""
        self.highlighted_square = square
        self.update()
    
    def highlight_move_path(self, from_square, to_square):
        """Highlight the full path of a move from origin to destination."""
        self.highlighted_path.clear()
        
        # Add both origin and destination squares
        self.highlighted_path.add(from_square)
        self.highlighted_path.add(to_square)
        
        # For sliding pieces (queen, rook, bishop), show the full path
        piece = self.board.piece_at(from_square)
        if piece:
            piece_type = piece.symbol().upper()
            if piece_type in ['Q', 'R', 'B']:
                # Calculate the path between squares
                path_squares = self._get_path_squares(from_square, to_square)
                self.highlighted_path.update(path_squares)
        
        self.highlighted_square = to_square
        self.update()
    
    def _get_path_squares(self, from_square, to_square):
        """Get all squares in the path between two squares for sliding pieces."""
        from_file = chess.square_file(from_square)
        from_rank = chess.square_rank(from_square)
        to_file = chess.square_file(to_square)
        to_rank = chess.square_rank(to_square)
        
        squares = set()
        
        # Horizontal movement (rook, queen)
        if from_rank == to_rank:
            start_file = min(from_file, to_file)
            end_file = max(from_file, to_file)
            for file in range(start_file, end_file + 1):
                squares.add(chess.square(file, from_rank))
        
        # Vertical movement (rook, queen)
        elif from_file == to_file:
            start_rank = min(from_rank, to_rank)
            end_rank = max(from_rank, to_rank)
            for rank in range(start_rank, end_rank + 1):
                squares.add(chess.square(from_file, rank))
        
        # Diagonal movement (bishop, queen)
        elif abs(from_file - to_file) == abs(from_rank - to_rank):
            file_step = 1 if to_file > from_file else -1
            rank_step = 1 if to_rank > from_rank else -1
            file, rank = from_file, from_rank
            while file != to_file + file_step:
                squares.add(chess.square(file, rank))
                file += file_step
                rank += rank_step
        
        return squares
    
    def clear_highlight(self):
        """Clear the table hover highlight."""
        self.highlighted_square = None
        self.highlighted_path.clear()
        self.update()


# ---------------------------------------------------------------------------
#                         MOVE LIST & STATS TABLE
# ---------------------------------------------------------------------------
class MoveList(QTextEdit):
    """Simple QTextEdit showing SAN move list (read‑only)."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(50)
        self.setMaximumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(
            """
            QTextEdit {
                background: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 6px;
                color: #e0e0e0;
            }
            """
        )

    def set_moves(self, moves: List[str]):
        self.setHtml(" ".join(moves))


class StatsTable(QTableWidget):
    """Table of move statistics with sensible defaults for resizing."""

    HEADERS = [
        "Move",
        "Score",
        "Perf",
        "Decis.",
        "Wins",
        "Losses",
        "Draws",
        "Total",
        "Conf.",
    ]

    def __init__(self):
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        for i in range(len(self.HEADERS)):
            # Make all columns manually resizable
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            # Set initial column widths
            if i == 0:  # Move column
                self.setColumnWidth(i, 80)
            elif i == 1:  # Score column
                self.setColumnWidth(i, 70)
            elif i == 8:  # Confidence column
                self.setColumnWidth(i, 60)
            else:  # Other columns
                self.setColumnWidth(i, 80)
        self.setAlternatingRowColors(True)
        self.setStyleSheet(
            """
            QTableWidget {
                background: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                color: #e0e0e0;
                gridline-color: #404040;
            }
            QTableWidget::item {
                padding: 4px;
                border: none;
            }
            QTableWidget::item:selected {
                background: #404040;
                color: #ffffff;
            }
            QHeaderView::section {
                background: #1e1e1e;
                color: #e0e0e0;
                padding: 6px;
                border: 1px solid #404040;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background: #404040;
            }
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)
        self.verticalHeader().setDefaultSectionSize(24)
        
        # Enable mouse tracking for hover events
        self.setMouseTracking(True)
        
        # Store move data for highlighting
        self.move_data = []
        self.board_widget = None  # Will be set by MainWindow
        
        # Connect header clicks to sorting
        self.horizontalHeader().sectionClicked.connect(self._handle_header_click)

    def _handle_header_click(self, logical_index):
        """Handle header clicks for custom sorting"""
        if not self.move_data:
            return
            
        # Get current sort order
        current_order = self.horizontalHeader().sortIndicatorOrder()
        new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        
        # Sort the data
        self._sort_data(logical_index, new_order)
        
        # Update the table
        self.populate(self.move_data)
        
        # Update sort indicator
        self.horizontalHeader().setSortIndicator(logical_index, new_order)

    def _sort_data(self, column, order):
        """Sort the move_data based on column and order"""
        if not self.move_data:
            return
            
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        if column == 0:  # Move column - sort by UCI move
            self.move_data.sort(key=lambda x: x.move, reverse=reverse)
        elif column == 1:  # Score column - sort by evaluation score
            self.move_data.sort(key=lambda x: x.evaluation_score, reverse=reverse)
        elif column == 2:  # Performance column - sort by performance score
            self.move_data.sort(key=lambda x: x.performance_score, reverse=reverse)
        elif column == 3:  # Decisiveness column - sort by decisiveness score
            self.move_data.sort(key=lambda x: x.decisiveness_score, reverse=reverse)
        elif column == 4:  # Wins column - sort by wins
            self.move_data.sort(key=lambda x: x.wins, reverse=reverse)
        elif column == 5:  # Losses column - sort by losses
            self.move_data.sort(key=lambda x: x.losses, reverse=reverse)
        elif column == 6:  # Draws column - sort by draws
            self.move_data.sort(key=lambda x: x.draws, reverse=reverse)
        elif column == 7:  # Total column - sort by total games
            self.move_data.sort(key=lambda x: x.total_games, reverse=reverse)
        elif column == 8:  # Confidence column - sort by confidence level
            confidence_order = {"high": 3, "medium": 2, "low": 1}
            self.move_data.sort(key=lambda x: confidence_order.get(x.confidence_level, 0), reverse=reverse)
    
    # DataManager provides list-like stats objects; we just map.
    def populate(self, stats):
        self.setRowCount(len(stats))
        self.move_data = stats  # Store the stats for hover highlighting
        
        # Create a temporary board to convert UCI moves to SAN
        temp_board = chess.Board()
        
        for r, s in enumerate(stats):
            # Calculate win rate for color coding
            win_rate = s.wins / s.total_games if s.total_games > 0 else 0
            
            # Format evaluation score as +0.23 or -0.45
            score_str = f"{s.evaluation_score/100:+.2f}" if s.evaluation_score != 0 else "0.00"
            
            # Convert UCI move to SAN notation
            try:
                move = chess.Move.from_uci(s.move)
                san_move = temp_board.san(move)
            except Exception:
                # Fallback to UCI if conversion fails
                san_move = s.move
            
            items = [
                san_move,
                score_str,
                f"{s.performance_score:.3f}",
                f"{s.decisiveness_score:.3f}",
                str(s.wins),
                str(s.losses),
                str(s.draws),
                str(s.total_games),
                s.confidence_level,
            ]
            for c, text in enumerate(items):
                itm = QTableWidgetItem(text)
                itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Color coding based on column type
                if c == 1:  # Score column
                    if s.evaluation_score > 20:
                        itm.setBackground(QColor(76, 175, 80))  # Green for positive score
                    elif s.evaluation_score < -20:
                        itm.setBackground(QColor(244, 67, 54))  # Red for negative score
                    else:
                        itm.setBackground(QColor(255, 152, 0))  # Orange for neutral
                    itm.setForeground(QColor("white"))
                elif c == 2:  # Performance score
                    if s.performance_score > 0.6:
                        itm.setBackground(QColor(76, 175, 80))  # Green for good performance
                    elif s.performance_score < 0.4:
                        itm.setBackground(QColor(244, 67, 54))  # Red for poor performance
                    else:
                        itm.setBackground(QColor(255, 152, 0))  # Orange for neutral
                    itm.setForeground(QColor("white"))
                elif c == 3:  # Decisiveness
                    if s.decisiveness_score > 0.7:
                        itm.setBackground(QColor(156, 39, 176))  # Purple for high decisiveness
                    elif s.decisiveness_score < 0.3:
                        itm.setBackground(QColor(158, 158, 158))  # Gray for low decisiveness
                    else:
                        itm.setBackground(QColor(255, 152, 0))  # Orange for medium
                    itm.setForeground(QColor("white"))
                elif c == 4:  # Wins
                    itm.setBackground(QColor(76, 175, 80, 100))  # Light green
                elif c == 5:  # Losses
                    itm.setBackground(QColor(244, 67, 54, 100))  # Light red
                elif c == 6:  # Draws
                    itm.setBackground(QColor(158, 158, 158, 100))  # Light gray
                elif c == 7:  # Total games
                    if s.total_games > 100:
                        itm.setBackground(QColor(33, 150, 243, 100))  # Light blue for high volume
                    elif s.total_games < 10:
                        itm.setBackground(QColor(255, 193, 7, 100))  # Light yellow for low volume
                elif c == 8:  # Confidence
                    bg = QColor(get_confidence_color(s.confidence_level))
                    itm.setBackground(bg)
                    itm.setForeground(QColor("white"))
                
                self.setItem(r, c, itm)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events to highlight moves on the board."""
        super().mouseMoveEvent(event)
        
        if not self.board_widget or not self.move_data:
            return
            
        # Get the item under the mouse cursor
        item = self.itemAt(event.pos())
        if item:
            row = item.row()
            if 0 <= row < len(self.move_data):
                # Get the move from the stats data
                move_uci = self.move_data[row].move
                try:
                    # Convert UCI move to chess.Move object
                    move = chess.Move.from_uci(move_uci)
                    # Highlight the full move path from origin to destination
                    self.board_widget.highlight_move_path(move.from_square, move.to_square)
                except Exception:
                    # If move conversion fails, clear highlighting
                    self.board_widget.clear_highlight()
        else:
            # If mouse is not over any item, clear highlighting
            self.board_widget.clear_highlight()
    
    def leaveEvent(self, event):
        """Clear highlighting when mouse leaves the table."""
        super().leaveEvent(event)
        if self.board_widget:
            self.board_widget.clear_highlight()
    
    def mousePressEvent(self, event):
        """Handle mouse click events to play moves on the board."""
        super().mousePressEvent(event)
        
        if not self.board_widget or not self.move_data:
            return
            
        # Get the item under the mouse cursor
        item = self.itemAt(event.pos())
        if item:
            row = item.row()
            if 0 <= row < len(self.move_data):
                # Get the move from the stats data
                move_uci = self.move_data[row].move
                try:
                    # Convert UCI move to chess.Move object
                    move = chess.Move.from_uci(move_uci)
                    # Play the move on the board
                    self.board_widget.push_move(move)
                except Exception as e:
                    logger.error(f"Failed to play move {move_uci}: {e}")


# ---------------------------------------------------------------------------
#                            MAIN  APPLICATION
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow, ThemeMixin):
    """Top‑level window wiring up all widgets & background workers."""
    
    def __init__(self):
        super().__init__()
        self._init_theme()
        # Initialize data manager in background to avoid blocking GUI launch
        self.data_manager = None
        self._init_data_manager_async()
        self.current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self._logged_missing_datasets = set()  # Cache for missing dataset warnings
        self._init_ui()
        self._init_signals()
        self._timer = QTimer(interval=2000, timeout=self._poll_updates)
        self._timer.start()
    
    def _init_data_manager_async(self):
        """Initialize data manager in background thread"""
        def init_worker():
            try:
                from data_manager import DataManager
                self.data_manager = DataManager()
                logger.info("Data manager initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing data manager: {e}")
                # Create a minimal data manager for fallback
                self.data_manager = self._create_fallback_data_manager()
        
        # Start initialization in background thread
        import threading
        thread = threading.Thread(target=init_worker, daemon=True)
        thread.start()
    
    def _create_fallback_data_manager(self):
        """Create a minimal fallback data manager"""
        class FallbackDataManager:
            def get_position_stats(self, fen, network=None):
                return []
            def _generate_sample_stats(self, fen, network=None):
                return []
            def download_position_specific_data(self, fen, network=None):
                return True
        
        return FallbackDataManager()

    # ------------------------------------------------------------------
    #                               UI
    # ------------------------------------------------------------------
    def _init_ui(self):
        self.setWindowTitle("Chess Opening Explorer – Enhanced")
        self.resize(1200, 800)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("QMainWindow{background:#1e1e1e;}")

        # -------- Toolbar (Zoom control) ----------
        toolbar = QToolBar("Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: #2d2d2d;
                border: 1px solid #404040;
                spacing: 6px;
                padding: 4px;
            }
            QToolBar QLabel {
                color: #e0e0e0;
                font-weight: bold;
            }
            QToolBar QSlider {
                background: transparent;
            }
            QToolBar QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 8px;
                background: #1e1e1e;
                border-radius: 4px;
            }
            QToolBar QSlider::handle:horizontal {
                background: #606060;
                border: 1px solid #404040;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QToolBar QSlider::handle:horizontal:hover {
                background: #808080;
            }
        """)
        zoom_slider = QSlider(Qt.Orientation.Horizontal, minimum=50, maximum=200, value=100)
        zoom_slider.setMinimumWidth(100)
        zoom_slider.setMaximumWidth(200)
        zoom_slider.setToolTip("Board zoom – 50 % to 200 %")
        toolbar.addWidget(QLabel("Zoom:"))
        toolbar.addWidget(zoom_slider)
        self.addToolBar(toolbar)

        # -------- Central Splitter (left | right) ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # ***** LEFT STACK *****
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(8)

        self.board = ChessBoardWidget()
        left_layout.addWidget(self.board, stretch=4)

        # Move list under board
        self.move_list = MoveList()
        left_layout.addWidget(self.move_list, stretch=1)

        # Control panel in scroll area so it never gets clipped.
        self.ctrl_panel = self._build_control_panel()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.ctrl_panel)
        scroll.setMinimumHeight(120)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #808080;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        left_layout.addWidget(scroll, stretch=2)

        splitter.addWidget(left_widget)

        # ***** RIGHT STACK *****
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(8)

        stats_label = QLabel("Move Statistics")
        stats_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 0px;
            }
        """)
        right_layout.addWidget(stats_label)
        self.stats_table = StatsTable()
        # Connect the table to the board for hover highlighting
        self.stats_table.board_widget = self.board
        right_layout.addWidget(self.stats_table)

        self.status = QLabel("Ready")
        self.status.setFrameShape(QFrame.Shape.Panel)
        self.status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.status.setStyleSheet("QLabel{background:#2d2d2d;color:#e0e0e0;padding:6px;border:1px solid #404040;border-radius:4px;}")
        right_layout.addWidget(self.status)

        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # Initial populate
        self._refresh_all()

        # --- keep ref ---
        self._zoom_slider = zoom_slider

    # ------------------------------------------------------------------
    #                          CONTROL PANEL
    # ------------------------------------------------------------------
    def _build_control_panel(self) -> QWidget:
        p = QWidget()
        p.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        p.setStyleSheet("""
            QWidget {
                background: #2d2d2d;
                color: #e0e0e0;
            }
            QComboBox {
                background: #1e1e1e;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 2px 4px;
                color: #e0e0e0;
                font-size: 11px;
                min-width: 60px;
                max-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background: #1e1e1e;
                border: 1px solid #404040;
                color: #e0e0e0;
                selection-background-color: #404040;
            }
            QPushButton {
                background: #404040;
                border: 1px solid #606060;
                border-radius: 3px;
                padding: 2px 8px;
                color: #e0e0e0;
                font-weight: bold;
                font-size: 11px;
                min-width: 60px;
                max-width: 120px;
            }
            QPushButton:hover {
                background: #606060;
                border: 1px solid #808080;
            }
            QPushButton:pressed {
                background: #1e1e1e;
            }
            QPushButton:checked {
                background: #0066cc;
                border: 1px solid #0088ff;
            }
            QSpinBox {
                background: #1e1e1e;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 2px 4px;
                color: #e0e0e0;
                font-size: 11px;
                min-width: 60px;
                max-width: 120px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #404040;
                border: 1px solid #606060;
                border-radius: 2px;
                width: 12px;
                height: 10px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #606060;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
            }
        """)
        vbox = QVBoxLayout(p)
        vbox.setSpacing(4)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Compact horizontal layout for all controls ---
        controls_row = QHBoxLayout()
        controls_row.setSpacing(4)
        controls_row.setContentsMargins(0, 0, 0, 0)

        # Network selector
        net = QComboBox()
        net.addItems(["All Networks", "T70", "T80", "T90"])
        self._net_combo = net
        controls_row.addWidget(QLabel("Network:"))
        controls_row.addWidget(net)

        # Side selector
        self.white_btn = QPushButton("White", checkable=True, checked=True)
        self.black_btn = QPushButton("Black", checkable=True)
        for b in (self.white_btn, self.black_btn):
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            b.setMinimumWidth(40)
            b.setMaximumWidth(60)
            b.setMinimumHeight(20)
            b.setMaximumHeight(28)
            b.setFont(QFont("Arial", 9))
        controls_row.addWidget(self.white_btn)
        controls_row.addWidget(self.black_btn)

        # Min number of games parameter
        self.min_games_spin = QSpinBox()
        self.min_games_spin.setRange(0, 10000)
        self.min_games_spin.setValue(0)
        self.min_games_spin.setSingleStep(10)
        self.min_games_spin.setMinimumWidth(60)
        self.min_games_spin.setMaximumWidth(80)
        controls_row.addWidget(QLabel("Min Games:"))
        controls_row.addWidget(self.min_games_spin)

        # Dataset selector
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["All Datasets", "lichess_2023", "lichess_2022", "lichess_2021"])
        controls_row.addWidget(QLabel("Dataset:"))
        controls_row.addWidget(self.dataset_combo)

        # Download button
        self.download_btn = QPushButton("Download")
        controls_row.addWidget(self.download_btn)

        # Export buttons
        self.pgn_btn = QPushButton("PGN")
        self.json_btn = QPushButton("JSON")
        controls_row.addWidget(self.pgn_btn)
        controls_row.addWidget(self.json_btn)

        controls_row.addStretch(1)
        vbox.addLayout(controls_row)
        vbox.addStretch(1)
        return p

    @staticmethod
    def _group(title: str, widget: QWidget) -> QGroupBox:
        g = QGroupBox(title)
        g.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(g)
        lay.addWidget(widget)
        g.setStyleSheet(
            "QGroupBox{font-weight:bold;color:#e0e0e0;border:1px solid #404040;border-radius:6px;padding:4px;background:#2d2d2d;}"
        )
        return g

    # ------------------------------------------------------------------
    #                      SIGNALS / SLOTS / BACKGROUND
    # ------------------------------------------------------------------
    def _init_signals(self):
        self._zoom_slider.valueChanged.connect(self.board.set_zoom)
        self.white_btn.clicked.connect(lambda: self._toggle_side("white"))
        self.black_btn.clicked.connect(lambda: self._toggle_side("black"))
        self._net_combo.currentTextChanged.connect(lambda *_: self._refresh_all())
        self.board.move_callback = self._board_position_changed
        self.dataset_combo.currentTextChanged.connect(self._refresh_all)
        self.download_btn.clicked.connect(self._download_dataset)
        self.pgn_btn.clicked.connect(self._export_pgn)
        self.json_btn.clicked.connect(self._export_json)
        self.min_games_spin.valueChanged.connect(self._refresh_all)

    # ------------------------------------------------------------------
    #                           CORE LOGIC
    # ------------------------------------------------------------------
    def _toggle_side(self, side: str):
        if side == "white":
            self.white_btn.setChecked(True)
            self.black_btn.setChecked(False)
        else:
            self.white_btn.setChecked(False)
            self.black_btn.setChecked(True)
        self._refresh_all()

    def _board_position_changed(self):
        self.current_fen = self.board.get_fen()
        self._refresh_all()

    def _refresh_all(self):
        # Fetch (async) data for position/network.
        network = None if self._net_combo.currentText() == "All Networks" else self._net_combo.currentText()
        dataset = None if self.dataset_combo.currentText() == "All Datasets" else self.dataset_combo.currentText()
        min_games = self.min_games_spin.value()
        
        try:
            # Check if data manager is initialized
            if self.data_manager is None:
                self.status.setText("Initializing data manager...")
                return
            
            # Use position-specific data fetching instead of complete dataset downloads
            stats = self.data_manager.get_position_stats(self.current_fen, network, min_games=min_games)
            if stats:
                self._update_stats_table_with_data(stats)
                self._update_move_list_with_data(stats)
                self.status.setText(f"Position analysis: {len(stats)} moves found")
            else:
                # Generate sample data for the current position
                stats = self.data_manager._generate_sample_stats(self.current_fen, network, min_games=min_games)
                if stats:
                    self._update_stats_table_with_data(stats)
                    self._update_move_list_with_data(stats)
                    self.status.setText(f"Sample data: {len(stats)} moves for current position")
                else:
                    self._update_stats_table_with_data([])
                    self._update_move_list_with_data([])
                    self.status.setText("No moves available for this position")
        except Exception as exc:
            logger.warning("Data fetch failed: %s", exc)
            self._update_stats_table_with_data([])
            self._update_move_list_with_data([])
            self.status.setText("⚠️ Error loading data - using sample data")

    def _update_stats_table(self, network):
        stats = self.data_manager.get_position_stats(self.current_fen, network) or []
        self.stats_table.populate(stats)
        if stats:
            self.status.setText(f"{len(stats)} moves found for position")
        else:
            self.status.setText("No moves available for this position")

    def _update_stats_table_with_data(self, stats):
        """Update stats table with provided data"""
        self.stats_table.populate(stats)
        if stats:
            self.status.setText(f"{len(stats)} moves found for position")
        else:
            self.status.setText("No moves available for this position")

    def _update_move_list(self, network):
        stats = self.data_manager.get_position_stats(self.current_fen, network) or []
        moves = []
        board = chess.Board(self.current_fen)
        for st in sorted(stats, key=lambda s: s.performance_score, reverse=True)[:8]:
            try:
                san = board.san(chess.Move.from_uci(st.move))
                moves.append(san)
            except Exception:  # pragma: no‑cover – defensive
                continue
        self.move_list.set_moves(moves)

    def _update_move_list_with_data(self, stats):
        """Update move list with provided data"""
        moves = []
        board = chess.Board(self.current_fen)
        for st in sorted(stats, key=lambda s: s.performance_score, reverse=True)[:8]:
            try:
                san = board.san(chess.Move.from_uci(st.move))
                moves.append(san)
            except Exception:  # pragma: no‑cover – defensive
                continue
        self.move_list.set_moves(moves)

    def _poll_updates(self):
        # Called every 2 s for background refresh.
        network = None if self._net_combo.currentText() == "All Networks" else self._net_combo.currentText()
        dataset = None if self.dataset_combo.currentText() == "All Datasets" else self.dataset_combo.currentText()
        min_games = self.min_games_spin.value()
        
        try:
            # Check if data manager is initialized
            if self.data_manager is None:
                self.status.setText("Initializing data manager...")
                return
            
            # Use position-specific data fetching instead of complete dataset downloads
            stats = self.data_manager.get_position_stats(self.current_fen, network, min_games=min_games)
            if stats:
                self._update_stats_table_with_data(stats)
                self._update_move_list_with_data(stats)
                self.status.setText(f"Position analysis: {len(stats)} moves found")
            else:
                # Generate sample data for the current position
                stats = self.data_manager._generate_sample_stats(self.current_fen, network, min_games=min_games)
                if stats:
                    self._update_stats_table_with_data(stats)
                    self._update_move_list_with_data(stats)
                    self.status.setText(f"Sample data: {len(stats)} moves for current position")
                else:
                    self._update_stats_table_with_data([])
                    self._update_move_list_with_data([])
                    self.status.setText("No moves available for this position")
        except Exception as exc:
            logger.warning("Poll update failed: %s", exc)
            self._update_stats_table_with_data([])
            self._update_move_list_with_data([])
            self.status.setText("⚠️ Error loading data - using sample data")

    # ------------------------------------------------------------------
    #                             ACTIONS
    # ------------------------------------------------------------------
    def _download_dataset(self):
        """Download position-specific data for the current position"""
        try:
            if self.data_manager is None:
                self.status.setText("Data manager not initialized yet...")
                return
            
            logger.info("Downloading position-specific data for current position")
            success = self.data_manager.download_position_specific_data(self.current_fen)
            if success:
                self.status.setText("Position-specific data downloaded successfully")
                # Refresh the display
                self._refresh_all()
            else:
                self.status.setText("Failed to download position-specific data")
        except Exception as exc:
            logger.error(f"Dataset download failed: {exc}")
            self.status.setText(f"Dataset download failed: {exc}")

    def _export_pgn(self):
        try:
            with open("position.pgn", "w") as f:
                f.write(chess.Board(self.current_fen).epd())
            self.status.setText("Saved position.pgn")
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")

    def _export_json(self):
        try:
            with open("position.json", "w") as f:
                json.dump({"fen": self.current_fen, "ts": time.time()}, f, indent=2)
            self.status.setText("Saved position.json")
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")

    # ------------------------------------------------------------------
    #                            CLEANUP
    # ------------------------------------------------------------------
    def resizeEvent(self, event):  # noqa: N802 – Qt signature
        """Handle window resize events"""
        super().resizeEvent(event)
        # Force board update to recalculate square sizes
        if hasattr(self, 'board'):
            self.board.update()
    
    def closeEvent(self, event):  # noqa: N802 – Qt signature
        # analysis_manager.stop_background_analysis() # This line was removed from the original file
        self._timer.stop()
        event.accept()


# ---------------------------------------------------------------------------
#                                    MAIN
# ---------------------------------------------------------------------------

def main():  # pragma: no‑cover
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
