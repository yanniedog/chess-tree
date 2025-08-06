# Chess Opening Explorer

A real-time, AI-theoretical chess opening explorer that dynamically reveals the objective performance of each move in an opening tree. The system is powered exclusively by engine self-play data (primarily LCZero) and provides statistically robust analysis for serious theoretical chess study.

## Features

### Core Functionality
- **Real-time Performance Analysis**: Displays performance scores calculated as `(wins + 0.5 * draws) / total_games`
- **Multiple Analysis Modes**: 
  - Performance Score (default)
  - Decisiveness Score (win % of decisive games only)
  - Full W/L/D breakdown
- **Network Version Filtering**: Filter results by specific LCZero network versions (T70, T80, T90, etc.)
- **Side Switching**: Switch between White and Black perspectives with real-time stat updates
- **Confidence Indicators**: Color-coded confidence levels based on game count (red <10, yellow 10-49, green ≥50)

### Data Management
- **FEN Normalization**: Deduplicates transpositions by normalizing FEN (ignoring halfmove clocks and move numbers)
- **Persistent Caching**: LMDB for game data, SQLite for statistics with network version tagging
- **Archive Index**: Lightweight FEN-to-archive mapping for efficient data lookup
- **Streaming Processing**: Processes archives with early termination at configurable thresholds
- **Resumable Downloads**: Bandwidth-throttled, resumable archive downloads

### User Interface
- **Interactive Chess Board**: PyQt6-based GUI with SVG board rendering
- **Move Tree Navigation**: Hierarchical move tree with back/forward navigation
- **Statistics Panel**: Comprehensive move statistics table with sorting
- **Control Panel**: Network filtering, side selection, analysis mode switching
- **Export Options**: PGN and JSON export for reproducibility

### Engine Integration
- **Separate Engine Analysis**: User-triggered engine analysis distinct from historical data
- **Multiple Engine Support**: Stockfish and other UCI engines
- **Background Analysis**: Predictive prefetching of likely next moves
- **Real-time Evaluation**: Engine analysis with configurable time/depth limits

### API Access
- **REST API**: Minimal REST API for external tool integration
- **CORS Support**: Cross-origin resource sharing enabled
- **Multiple Endpoints**: Stats, position info, engine analysis, export

## Installation

### Prerequisites
- Python 3.8 or higher
- Stockfish chess engine (optional, for engine analysis)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install Stockfish (Optional)
- **Windows**: Download from [Stockfish website](https://stockfishchess.org/download/)
- **macOS**: `brew install stockfish`
- **Linux**: `sudo apt-get install stockfish` or `sudo yum install stockfish`

## Usage

### GUI Mode (Default)
```bash
python main.py
# or
python main.py --mode gui
```

### API Server Mode
```bash
python main.py --mode api --host localhost --port 5000
```

### Data Processing Mode
```bash
python main.py --mode data
```

### Debug Mode
```bash
python main.py --debug
```

## Configuration

The system is configured through `config.py` with the following main sections:

### Cache Configuration
- `max_size_gb`: Maximum cache size in GB
- `lru_eviction`: Enable LRU cache eviction
- `cache_dir`: Cache directory path

### Network Configuration
- `timeout_seconds`: Network request timeout
- `max_retries`: Maximum download retries
- `bandwidth_limit_mbps`: Download bandwidth limit
- `resume_downloads`: Enable resumable downloads

### UI Configuration
- `board_size`: Chess board display size
- `auto_prefetch`: Enable automatic prefetching
- `prefetch_moves`: Number of moves to prefetch
- `confidence_thresholds`: Game count thresholds for confidence levels

### Data Configuration
- `lczero_base_url`: LCZero archive base URL
- `max_games_per_fen`: Maximum games to process per position
- `streaming_threshold`: Early termination threshold
- `normalize_fen`: Enable FEN normalization
- `deduplicate_transpositions`: Enable transposition deduplication

## API Endpoints

### Get Position Statistics
```
GET /api/stats/{fen}?network={network}&side={side}
```

### Get Position Information
```
GET /api/position/{fen}
```

### Engine Analysis
```
POST /api/analyze/{fen}
Content-Type: application/json
{
  "engine": "stockfish",
  "time_limit": 5000,
  "depth_limit": 20
}
```

### Export Position Data
```
GET /api/export/{fen}?format=json&network={network}
```

### Health Check
```
GET /api/health
```

### Available Engines
```
GET /api/engines
```

## Data Sources

The system is designed to work with LCZero self-play data archives. The data format expected is:

```
fen|move|result|timestamp
```

Where:
- `fen`: FEN string of the position
- `move`: UCI move string
- `result`: Game result ("1-0", "0-1", "1/2-1/2")
- `timestamp`: Unix timestamp

## Architecture

### Core Components
1. **DataManager**: Handles archive downloading, processing, and caching
2. **EngineManager**: Manages chess engine analysis
3. **ArchiveIndex**: Maintains FEN-to-archive mapping
4. **CacheManager**: LMDB and SQLite storage management
5. **GUI**: PyQt6-based user interface
6. **API Server**: Flask-based REST API

### Data Flow
1. User selects position → FEN normalization
2. Check local cache for statistics
3. If not cached, consult archive index
4. Download and process relevant archives
5. Aggregate statistics by network version
6. Display results with confidence indicators

### Caching Strategy
- **LMDB**: High-performance key-value store for game data
- **SQLite**: Relational database for aggregated statistics
- **Archive Index**: JSON file mapping FENs to archive files
- **LRU Eviction**: Automatic cache cleanup based on usage

## Development

### Project Structure
```
chess-tree/
├── main.py              # Main entry point
├── config.py            # Configuration settings
├── utils.py             # Utility functions
├── data_manager.py      # Data management system
├── engine_analyzer.py   # Engine analysis module
├── gui.py              # PyQt6 GUI
├── api_server.py       # REST API server
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Adding New Features
1. **New Data Sources**: Extend `ArchiveDownloader` class
2. **New Engines**: Add to `EngineManager.init_engines()`
3. **New Analysis Modes**: Extend `MoveStats` class
4. **New UI Components**: Add to `MainWindow` class
5. **New API Endpoints**: Add routes to `api_server.py`

### Testing
```bash
# Run with debug logging
python main.py --debug

# Test API endpoints
curl http://localhost:5000/api/health
curl http://localhost:5000/api/stats/rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201
```

## Performance Considerations

### Optimization Strategies
- **Streaming Processing**: Process archives without loading entire files
- **Early Termination**: Stop processing when threshold reached
- **Background Prefetching**: Predict and fetch likely next moves
- **LRU Cache**: Automatic cleanup of old data
- **Bandwidth Throttling**: Prevent network overload

### Memory Management
- **Configurable Cache Size**: Limit cache to prevent memory issues
- **Streaming Decompression**: Process compressed archives efficiently
- **Database Indexing**: Optimize SQLite queries with proper indexing

## Troubleshooting

### Common Issues

1. **No Data Available**
   - Check if LCZero archives are accessible
   - Verify archive index is populated
   - Check network connectivity

2. **Engine Analysis Fails**
   - Ensure Stockfish is installed and in PATH
   - Check engine permissions
   - Verify UCI protocol compatibility

3. **GUI Not Starting**
   - Install PyQt6: `pip install PyQt6`
   - Check display settings
   - Verify Python version compatibility

4. **API Server Issues**
   - Check port availability
   - Verify Flask installation
   - Check firewall settings

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
python main.py --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please see the LICENSE file for details.

## Acknowledgments

- **LCZero Team**: For providing the self-play data
- **Python-Chess**: For chess library functionality
- **Stockfish Team**: For the chess engine
- **PyQt6**: For the GUI framework 