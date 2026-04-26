# APEX — Autonomous Futures Trading System

Phase 1 foundation: scaffold, config, database, IBKR, kill switch, logger, CLI.

## Quick Start

```bash
pip install -r requirements.txt
python main.py --dry-run
python main.py --market NQ --profile conservative --dry-run
```

## Running Tests

```bash
pytest tests/ -v
```
