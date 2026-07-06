"""
Logging decorator for LangGraph nodes.

Wraps a node function so every invocation logs a clear "NODE INVOKED" /
"NODE COMPLETED" / "NODE FAILED" line, with timing, regardless of what the
node does internally. Node functions still log their own specific details
(rewritten query, retrieved chunks, etc.) — this decorator only guarantees
the graph's *shape* (which node ran, in what order, how long it took) is
always visible in the terminal.
"""

import logging
import time
from functools import wraps
from typing import Callable

from app.core.logging_config import log_section
from app.graph.state import RAGState

logger = logging.getLogger("rag.graph")


def log_node(node_name: str):
    def decorator(fn: Callable[[RAGState], dict]) -> Callable[[RAGState], dict]:
        @wraps(fn)
        def wrapper(state: RAGState) -> dict:
            log_section(logger, f"NODE INVOKED -> {node_name}")
            start = time.perf_counter()
            try:
                result = fn(state)
            except Exception:
                elapsed = (time.perf_counter() - start) * 1000
                logger.exception("NODE FAILED -> %s (after %.1fms)", node_name, elapsed)
                raise
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("NODE COMPLETED -> %s (%.1fms)", node_name, elapsed)
            return result

        return wrapper

    return decorator