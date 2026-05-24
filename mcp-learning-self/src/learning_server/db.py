"""Database helpers for SQLite journal and ChromaDB vector store."""

import os
import sqlite3
from datetime import datetime

DB_DIR = r"D:\Punokawan V2\data"
SQLITE_PATH = os.path.join(DB_DIR, "trading_journal.db")
CHROMA_PATH = os.path.join(DB_DIR, "chromadb")
PROFILES_PATH = os.path.join(DB_DIR, "trader_profiles.json")


def ensure_dirs():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(CHROMA_PATH, exist_ok=True)


def get_sqlite_connection() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(SQLITE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_sqlite_schema():
    conn = get_sqlite_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT,
            symbol TEXT DEFAULT 'XAUUSD',
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            sl REAL NOT NULL,
            tp REAL NOT NULL,
            exit_price REAL,
            lot_size REAL NOT NULL,
            pnl REAL,
            pnl_pct REAL,
            score INTEGER,
            confluence_reasons TEXT,
            patterns TEXT,
            session TEXT,
            day_of_week TEXT,
            verdict TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            symbol TEXT,
            timeframe TEXT,
            indicators_json TEXT,
            smc_json TEXT,
            chart_path TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (trade_id) REFERENCES trades(id)
        )
    """)
    conn.commit()
    conn.close()


def init_chroma_collections():
    """Initialize ChromaDB collections for avoidance database."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PATH)

        # Text embeddings collection (market conditions)
        try:
            client.get_collection("market_conditions")
        except Exception:
            client.create_collection(
                name="market_conditions",
                metadata={"description": "Market condition text embeddings for trade avoidance"}
            )

        # Chart image embeddings collection
        try:
            client.get_collection("chart_patterns")
        except Exception:
            client.create_collection(
                name="chart_patterns",
                metadata={"description": "Chart image embeddings for pattern similarity"}
            )

        return client
    except ImportError:
        return None
    except Exception:
        return None


# Initialize on import
ensure_dirs()
init_sqlite_schema()
