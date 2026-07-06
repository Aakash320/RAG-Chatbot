"""
Centralized logging configuration for the RAG pipeline.

Call `setup_logging()` once, at app startup (see app/main.py). Everything
else just does `logging.getLogger(__name__)` as usual — this module only
controls *how* those log lines are formatted and printed to the terminal.

Also provides a `request_id` contextvar so every log line emitted while
handling a single chat request can be tagged with the same short id,
making it easy to follow one request's full journey through the terminal
even when multiple requests overlap.
"""

import logging
import sys
import uuid
from contextvars import ContextVar

# ---------------------------------------------------------------------------
# Request correlation
# ---------------------------------------------------------------------------

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    """Generate and set a short request id for the current context."""
    rid = uuid.uuid4().hex[:8]
    _request_id_ctx.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id_ctx.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


# ---------------------------------------------------------------------------
# Colored console formatter
# ---------------------------------------------------------------------------


class _Color:
    GREY = "\x1b[38;20m"
    CYAN = "\x1b[36;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    MAGENTA = "\x1b[35;20m"
    BOLD = "\x1b[1m"
    RESET = "\x1b[0m"


_LEVEL_COLORS = {
    logging.DEBUG: _Color.GREY,
    logging.INFO: _Color.CYAN,
    logging.WARNING: _Color.YELLOW,
    logging.ERROR: _Color.RED,
    logging.CRITICAL: _Color.BOLD_RED,
}


class PipelineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, _Color.RESET)
        fmt = (
            f"{_Color.GREY}%(asctime)s{_Color.RESET} "
            f"{color}%(levelname)-8s{_Color.RESET} "
            f"{_Color.MAGENTA}[req:%(request_id)s]{_Color.RESET} "
            f"{_Color.BOLD}%(name)s{_Color.RESET} | %(message)s"
        )
        return logging.Formatter(fmt, datefmt="%H:%M:%S").format(record)


def setup_logging(level: int = logging.INFO) -> None:
    """Call once at startup. Replaces logging.basicConfig(...)."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(PipelineFormatter())
    handler.addFilter(_RequestIdFilter())
    root.addHandler(handler)

    # Quiet down noisy third-party loggers so pipeline logs stand out.
    for noisy in ("httpx", "httpcore", "urllib3", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Pretty-print helpers used throughout the pipeline
# ---------------------------------------------------------------------------

_BAR = "─" * 78


def log_section(logger: logging.Logger, title: str) -> None:
    """Visually separates one pipeline step from the next in the terminal."""
    logger.info(_BAR)
    logger.info("STEP: %s", title)


def log_kv(logger: logging.Logger, **fields) -> None:
    """Logs a set of key/value pairs, one per line, indented for readability."""
    for key, value in fields.items():
        logger.info("    %-18s %s", key + ":", value)


def truncate(text: str, length: int = 300) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[:length] + f"... [{len(text) - length} more chars]"