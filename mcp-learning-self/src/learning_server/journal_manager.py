"""Trade journal logging — SQLite + ChromaDB persistence."""

import json
from datetime import datetime

from .db import get_sqlite_connection, init_chroma_collections


def log_trading_journal(
    ticket_id: str = "",
    symbol: str = "XAUUSD",
    direction: str = "",
    entry: float = 0.0,
    sl: float = 0.0,
    tp: float = 0.0,
    lot_size: float = 0.0,
    score: int = 0,
    confluence_reasons: str = "",
    patterns: str = "",
    session: str = "",
    verdict: str = "",
    notes: str = "",
    indicators_json: str = "",
    smc_json: str = "",
    chart_path: str = "",
    market_conditions_text: str = "",
    exit_price: float = None,
    pnl: float = None,
) -> dict:
    """Log a trade to the journal database.

    Stores structured data in SQLite and optionally indexes
    market conditions in ChromaDB for later similarity search.
    """
    conn = get_sqlite_connection()
    now = datetime.now()

    day_of_week = now.strftime("%A")

    try:
        cursor = conn.execute(
            """INSERT INTO trades
               (ticket_id, symbol, direction, entry, sl, tp, exit_price,
                lot_size, pnl, score, confluence_reasons, patterns,
                session, day_of_week, verdict, notes, created_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(ticket_id), symbol, direction, entry, sl, tp,
                exit_price, lot_size, pnl, score, confluence_reasons, patterns,
                session, day_of_week, verdict, notes,
                now.isoformat(), now.isoformat() if exit_price else None,
            ),
        )
        trade_id = cursor.lastrowid

        # Store market snapshot
        if indicators_json or smc_json:
            conn.execute(
                """INSERT INTO market_snapshots
                   (trade_id, symbol, timeframe, indicators_json, smc_json, chart_path)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (trade_id, symbol, "H1", indicators_json, smc_json, chart_path),
            )

        conn.commit()

        # Index in ChromaDB if conditions text provided
        chroma_status = "skipped"
        if market_conditions_text:
            try:
                client = init_chroma_collections()
                if client:
                    collection = client.get_collection("market_conditions")
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    embedding = model.encode([market_conditions_text])[0]

                    collection.add(
                        ids=[f"trade_{trade_id}"],
                        embeddings=[embedding.tolist()],
                        metadatas=[{
                            "trade_id": trade_id,
                            "verdict": verdict,
                            "pnl": pnl or 0,
                            "direction": direction,
                            "created_at": now.isoformat(),
                        }],
                        documents=[market_conditions_text],
                    )
                    chroma_status = "indexed"
            except Exception as e:
                chroma_status = f"error: {e}"

        return {
            "journal_id": trade_id,
            "status": "logged",
            "chromadb_status": chroma_status,
            "created_at": now.isoformat(),
        }

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()
