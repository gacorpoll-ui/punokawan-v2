"""SQLite database initialization and connection."""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta

from .config import settings


def get_db_path() -> str:
    db_dir = os.path.dirname(settings.DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)
    return settings.DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            trial_ends_at TEXT,
            subscription_tier TEXT DEFAULT 'trial',
            subscription_ends_at TEXT,
            role TEXT DEFAULT 'user'
        );

        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            sl REAL NOT NULL,
            tp REAL NOT NULL,
            lot_size REAL DEFAULT 0.05,
            score REAL DEFAULT 0,
            rr_ratio REAL DEFAULT 0,
            confluence TEXT DEFAULT '',
            tp_source TEXT DEFAULT '',
            session TEXT DEFAULT '',
            exit_price REAL,
            pnl REAL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            closed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS performance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance REAL,
            equity REAL,
            open_positions INTEGER DEFAULT 0,
            daily_pnl REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            sharpe_ratio REAL DEFAULT 0,
            total_trades INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TEXT NOT NULL,
            expires_at TEXT,
            payment_ref TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()


# Initialize on import
init_db()
