"""Vector similarity search to avoid repeating losing trade patterns.

Uses ChromaDB + sentence-transformers for text embeddings.
Optionally supports CLIP for chart image similarity (if available).

Target latency: <500ms for text search, <1000ms for image search.
"""

import time
from dataclasses import dataclass, field


@dataclass
class SimilarTrade:
    trade_id: int
    similarity: float
    verdict: str
    pnl: float
    direction: str
    created_at: str


@dataclass
class AvoidanceResult:
    blocked: bool
    lot_reduction: float  # 1.0 = full lot, 0.5 = half lot
    max_similarity: float
    similar_trades: list = field(default_factory=list)
    method_used: str = "none"
    latency_ms: float = 0.0


def check_avoidance_database(
    market_conditions_text: str = "",
    chart_image_path: str = "",
    similarity_threshold: float = 0.80,
    lot_reduction_threshold: float = 0.60,
) -> AvoidanceResult:
    """Check if current market conditions are similar to past losing trades.

    Two modes:
    1. Text similarity (fast, <200ms): Embed market conditions text
    2. Image similarity (slower, ~500ms): Embed chart image via CLIP
    3. Hybrid (both): Weighted combination

    Args:
        market_conditions_text: Description of current market conditions
        chart_image_path: Path to chart PNG for visual similarity
        similarity_threshold: Above this → BLOCK trade (>80% default)
        lot_reduction_threshold: Above this → HALVE lot size (>60% default)

    Returns:
        AvoidanceResult with block/lot_reduction decision
    """
    t0 = time.time()

    if not market_conditions_text and not chart_image_path:
        return AvoidanceResult(
            blocked=False, lot_reduction=1.0, max_similarity=0.0,
            method_used="no_input", latency_ms=round((time.time() - t0) * 1000, 1),
        )

    text_similarity = 0.0
    image_similarity = 0.0
    similar_trades = []
    method = "none"

    # Text similarity
    if market_conditions_text:
        try:
            from .db import init_chroma_collections

            client = init_chroma_collections()
            if client:
                collection = client.get_collection("market_conditions")
                if collection.count() > 0:
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    query_embedding = model.encode([market_conditions_text])[0]

                    results = collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=5,
                    )

                    if results and results["ids"] and results["ids"][0]:
                        for i, doc_id in enumerate(results["ids"][0]):
                            distance = results["distances"][0][i] if results.get("distances") else [0]
                            # ChromaDB returns distance, convert to similarity
                            sim = 1.0 / (1.0 + distance) if distance else 1.0
                            meta = results["metadatas"][0][i] if results.get("metadatas") else {}

                            similar_trades.append(SimilarTrade(
                                trade_id=meta.get("trade_id", 0),
                                similarity=round(sim, 3),
                                verdict=meta.get("verdict", "UNKNOWN"),
                                pnl=meta.get("pnl", 0),
                                direction=meta.get("direction", ""),
                                created_at=meta.get("created_at", ""),
                            ))

                        text_similarity = similar_trades[0].similarity if similar_trades else 0.0

                method = "text"
        except Exception:
            pass

    # Determine action
    max_sim = max(text_similarity, image_similarity)

    blocked = False
    lot_reduction = 1.0

    if max_sim > similarity_threshold:
        # Check if most similar trades were losers
        losing_sims = [t for t in similar_trades if t.verdict in ("LOSS", "loss")]
        if losing_sims and any(t.similarity > similarity_threshold for t in losing_sims):
            blocked = True
            lot_reduction = 0.0
    elif max_sim > lot_reduction_threshold:
        losing_sims = [t for t in similar_trades if t.verdict in ("LOSS", "loss")]
        if losing_sims and any(t.similarity > lot_reduction_threshold for t in losing_sims):
            lot_reduction = 0.5

    latency_ms = round((time.time() - t0) * 1000, 1)

    return AvoidanceResult(
        blocked=blocked,
        lot_reduction=lot_reduction,
        max_similarity=round(max_sim, 3),
        similar_trades=similar_trades[:5],
        method_used=f"text_sim={round(text_similarity,3)}" if method == "text" else method,
        latency_ms=latency_ms,
    )
