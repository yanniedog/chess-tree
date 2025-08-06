# Chess Dataset Analyzer

## Overview

The chess program has been modified to use local datasets instead of constantly calling Stockfish. This provides several benefits:

- **No Stockfish dependency**: The program no longer requires Stockfish to be installed
- **Faster analysis**: Local dataset queries are much faster than engine analysis
- **Real game data**: Analysis is based on actual games played by humans
- **Offline capability**: Once datasets are downloaded, the program works completely offline
- **Statistical insights**: Provides win/loss/draw statistics for each move

## How It Works

### Dataset Sources

The program can download chess datasets from Lichess:
- **lichess_2023**: Lichess rated games 2023 (1500MB)
- **lichess_2022**: Lichess rated games 2022 (1400MB)  
- **lichess_2021**: Lichess rated games 2021 (1300MB)

### Analysis Process

1. **Position Analysis**: When you analyze a position, the program:
   - Checks the local database for move statistics
   - Calculates performance scores based on win/loss/draw ratios
   - Provides evaluation scores in centipawns
   - Shows confidence levels based on the number of games

2. **Move Statistics**: For each move, you get:
   - **Wins/Losses/Draws**: Actual game results
   - **Performance Score**: (Wins + 0.5 × Draws) / Total Games
   - **Evaluation Score**: Converted to centipawns
   - **Confidence Level**: Based on number of games (low/medium/high)

### Sample Data

When no datasets are downloaded, the program generates realistic sample data for common chess positions to demonstrate the functionality.

## Usage

### GUI Interface

1. **Dataset Selection**: Use the "Dataset" dropdown to select which dataset to analyze
2. **Download Datasets**: Click "Download Dataset" to download and process a dataset
3. **Analysis**: The program automatically analyzes positions as you move pieces

### Command Line

```bash
# Test the dataset analyzer
python test_dataset.py

# Run the demo
python demo_dataset.py

# Run the GUI
python gui.py
```

## File Structure

```
chess-tree/
├── dataset_analyzer.py      # Main dataset analysis module
├── cache/
│   ├── datasets/           # Downloaded dataset files
│   └── dataset_stats.db    # SQLite database with move statistics
├── test_dataset.py         # Test script
├── demo_dataset.py         # Demo script
└── gui.py                 # Updated GUI with dataset support
```

## Key Components

### DatasetAnalyzer Class
- Manages dataset downloads and processing
- Provides position analysis using local data
- Handles caching for performance

### DatasetDownloader Class
- Downloads chess datasets from Lichess
- Manages dataset metadata and information

### DatasetProcessor Class
- Processes PGN files to extract move statistics
- Stores data in SQLite database for fast queries

## Benefits Over Stockfish

| Feature | Stockfish | Dataset Analyzer |
|---------|-----------|------------------|
| **Installation** | Requires Stockfish binary | No external dependencies |
| **Speed** | Slow (engine calculation) | Fast (database lookup) |
| **Data Source** | Engine evaluation | Real game statistics |
| **Offline** | Requires engine | Works offline |
| **Insights** | Engine evaluation | Win/loss/draw statistics |
| **Confidence** | Based on depth | Based on game count |

## Configuration

The dataset analyzer uses the same configuration system as the rest of the program. Key settings in `config.py`:

```python
# Cache settings
cache.max_size_gb = 0.1  # Cache size limit
cache.cache_dir = Path("cache")  # Cache directory

# Network settings  
network.timeout_seconds = 30  # Download timeout
network.chunk_size = 8192     # Download chunk size
```

## Future Enhancements

- **More datasets**: Add support for other chess databases
- **Advanced statistics**: Include rating ranges, time controls, etc.
- **Real-time updates**: Download new games as they become available
- **Custom datasets**: Allow users to import their own game collections

## Troubleshooting

### No datasets available
- The program will use sample data for demonstration
- Download a dataset using the GUI or command line

### Download fails
- Check internet connection
- Verify sufficient disk space (datasets are 1-1.5GB each)
- Try downloading a smaller dataset first

### Analysis shows no moves
- Ensure the position is valid
- Check that datasets have been processed correctly
- Verify the database file exists in cache/

## Migration from Stockfish

The program automatically detects when Stockfish is not available and falls back to dataset analysis. The GUI has been updated to show dataset information instead of engine controls.

All existing functionality remains the same - you can still:
- Analyze positions
- View move statistics  
- Export positions
- Use the interactive board

The main difference is that analysis is now based on real game data rather than engine calculations. 