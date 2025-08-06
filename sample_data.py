# Sample LCZero Data for Chess Opening Explorer
# This shows what the system would display with real archive data

SAMPLE_POSITION_DATA = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": {
        "moves": [
            {
                "move": "e2e4",
                "performance_score": 0.523,
                "decisiveness_score": 0.312,
                "wins": 1250,
                "losses": 1180,
                "draws": 570,
                "total_games": 3000,
                "confidence_level": "high"
            },
            {
                "move": "d2d4", 
                "performance_score": 0.518,
                "decisiveness_score": 0.298,
                "wins": 1100,
                "losses": 1050,
                "draws": 850,
                "total_games": 3000,
                "confidence_level": "high"
            },
            {
                "move": "c2c4",
                "performance_score": 0.512,
                "decisiveness_score": 0.305,
                "wins": 950,
                "losses": 920,
                "draws": 1130,
                "total_games": 3000,
                "confidence_level": "high"
            },
            {
                "move": "g1f3",
                "performance_score": 0.508,
                "decisiveness_score": 0.289,
                "wins": 880,
                "losses": 870,
                "draws": 1250,
                "total_games": 3000,
                "confidence_level": "high"
            }
        ],
        "network": "T80",
        "source_files": ["lczero_t80_archive_2023.gz"]
    }
}

# What the GUI would show:
# - Statistics table with 4 moves (e4, d4, c4, Nf3)
# - Performance scores around 0.51-0.52
# - High confidence levels (3000+ games each)
# - Move tree would show: [e4] [d4] [c4] [Nf3]
# - Status bar: "Found 4 moves with data"
# - Green highlighting for legal moves when pieces are selected 