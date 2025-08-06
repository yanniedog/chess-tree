"""
Minimal REST API server for external tools
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
from typing import Dict, List, Optional

from data_manager import DataManager
from utils import normalize_fen, get_logger, fetch_lichess_api

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize data manager
data_manager = DataManager()
logger = get_logger()

@app.route('/api/stats/<fen>', methods=['GET'])
def get_position_stats(fen: str):
    """Get statistics for a position"""
    try:
        # Get query parameters
        network = request.args.get('network')
        side = request.args.get('side', 'white')
        
        # Normalize FEN
        normalized_fen = normalize_fen(fen)
        
        # Get statistics
        stats = data_manager.get_position_stats(normalized_fen, network)
        
        # Convert to JSON-serializable format
        result = []
        for stat in stats:
            result.append({
                "move": stat.move,
                "performance_score": stat.performance_score,
                "decisiveness_score": stat.decisiveness_score,
                "wins": stat.wins,
                "losses": stat.losses,
                "draws": stat.draws,
                "total_games": stat.total_games,
                "confidence_level": stat.confidence_level,
                "network": stat.network,
                "source_files": stat.source_files,
                "last_updated": stat.last_updated
            })
        # Fetch Lichess stats for this FEN
        logger = get_logger()
        lichess_data = None
        try:
            lichess_data = fetch_lichess_api(normalized_fen, endpoint="lichess")
            logger.info(f"Fetched Lichess stats for FEN {normalized_fen}: {lichess_data}")
        except Exception as e:
            logger.error(f"Failed to fetch Lichess stats for FEN {normalized_fen}: {e}")
        return jsonify({
            "fen": normalized_fen,
            "side": side,
            "stats": result,
            "total_moves": len(result),
            "lichess": lichess_data
        })
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/position/<fen>', methods=['GET'])
def get_position_info(fen: str):
    """Get general information about a position"""
    try:
        normalized_fen = normalize_fen(fen)
        
        # Get legal moves
        from utils import get_legal_moves
        legal_moves = get_legal_moves(normalized_fen)
        
        # Get basic stats
        stats = data_manager.get_position_stats(normalized_fen)
        total_games = sum(stat.total_games for stat in stats)
        
        return jsonify({
            "fen": normalized_fen,
            "legal_moves": legal_moves,
            "total_moves": len(legal_moves),
            "moves_with_data": len(stats),
            "total_games": total_games,
            "has_data": len(stats) > 0
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_positions():
    """Search for positions with specific criteria"""
    try:
        data = request.get_json()
        
        # Extract search criteria
        min_games = data.get('min_games', 0)
        network = data.get('network')
        side = data.get('side', 'white')
        
        # This would require implementing a search function in DataManager
        # For now, return a simple response
        return jsonify({
            "message": "Search functionality not yet implemented",
            "criteria": {
                "min_games": min_games,
                "network": network,
                "side": side
            }
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "data_manager": "available",
        "cache_size": "unknown"  # Could implement cache size checking
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache"""
    try:
        data_manager.cleanup_cache()
        return jsonify({"message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/engines', methods=['GET'])
def get_available_engines():
    """Get list of available engines"""
    try:
        from engine_analyzer import engine_manager
        engines = engine_manager.get_available_engines()
        
        engine_info = []
        for engine in engines:
            info = engine_manager.get_engine_info(engine)
            engine_info.append({
                "name": engine,
                "status": info.get("status", "unknown")
            })
        
        return jsonify({
            "engines": engine_info,
            "total": len(engines)
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze/<fen>', methods=['POST'])
def analyze_position(fen: str):
    """Analyze a position with engine"""
    try:
        data = request.get_json() or {}
        engine_name = data.get('engine', 'stockfish')
        time_limit = data.get('time_limit', 5000)  # 5 seconds default
        depth_limit = data.get('depth_limit')
        
        from engine_analyzer import engine_manager
        
        # Check if engine is available
        if engine_name not in engine_manager.get_available_engines():
            return jsonify({"error": f"Engine {engine_name} not available"}), 400
        
        # Perform analysis
        moves = engine_manager.analyze_position(
            fen, engine_name, time_limit, depth_limit
        )
        
        # Convert to JSON format
        result = []
        for move in moves:
            result.append({
                "move": move.move,
                "score": move.score,
                "depth": move.depth,
                "time_ms": move.time_ms,
                "pv": move.pv
            })
        
        return jsonify({
            "fen": fen,
            "engine": engine_name,
            "moves": result,
            "total_moves": len(result)
        })
        
    except Exception as e:
        logger.error(f"Analysis API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export/<fen>', methods=['GET'])
def export_position(fen: str):
    """Export position data in various formats"""
    try:
        format_type = request.args.get('format', 'json')
        network = request.args.get('network')
        
        normalized_fen = normalize_fen(fen)
        stats = data_manager.get_position_stats(normalized_fen, network)
        
        if format_type == 'json':
            result = {
                "fen": normalized_fen,
                "stats": []
            }
            
            for stat in stats:
                result["stats"].append({
                    "move": stat.move,
                    "performance_score": stat.performance_score,
                    "decisiveness_score": stat.decisiveness_score,
                    "wins": stat.wins,
                    "losses": stat.losses,
                    "draws": stat.draws,
                    "total_games": stat.total_games,
                    "confidence_level": stat.confidence_level,
                    "network": stat.network
                })
            
            return jsonify(result)
            
        elif format_type == 'pgn':
            import chess
            board = chess.Board(normalized_fen)
            pgn = board.epd()
            return pgn, 200, {'Content-Type': 'text/plain'}
            
        else:
            return jsonify({"error": f"Unsupported format: {format_type}"}), 400
            
    except Exception as e:
        logger.error(f"Export API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500

def run_api_server(host: str = 'localhost', port: int = 5000, debug: bool = False):
    """Run the API server"""
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_api_server() 