"""
Centralised logging for the trading bot.
Writes to both file and console with rotation.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_DIR = "logs"


def ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


class WindowsSafeRotatingHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that handles Windows file-locking gracefully.

    On Windows, ``os.rename`` fails with ``PermissionError`` if another
    process or thread holds a handle to the log file.  Instead of letting
    the logging framework emit a noisy traceback, we:

    1. Try the normal rename-based rollover.
    2. If that fails with ``PermissionError``, fall back to closing the
       current file, copying its content to the backup, then re-opening
       the original file with truncation.

    This keeps the app logging without interruption even when multiple
    Streamlit sessions log to the same file.
    """

    def doRollover(self) -> None:
        """Override: attempt normal rollover, fall back on PermissionError."""
        if self.stream:
            self.stream.close()
            self.stream = None

        try:
            super().doRollover()
            return
        except PermissionError:
            # Windows: the file is locked by another handle.
            # Fall through to copy+truncate fallback.
            pass

        # ── Fallback: copy & truncate ──────────────────────────
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}")
                dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}")
                if os.path.exists(sfn):
                    try:
                        os.replace(sfn, dfn)
                    except OSError:
                        pass
            dfn = self.rotation_filename(f"{self.baseFilename}.1")
            try:
                import shutil
                shutil.copy2(self.baseFilename, dfn)
            except OSError:
                pass

        # Re-open the log file with truncation
        self.mode = "w"
        self.stream = self._open()
        self.mode = "a"


def get_logger(name: str, level: int = logging.INFO,
               log_file: Optional[str] = None) -> logging.Logger:
    """Get or create a logger with console + rotating file handler."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured
    logger.setLevel(level)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(console)

    if log_file is None:
        ensure_log_dir()
        log_file = os.path.join(_LOG_DIR, f"robot_{datetime.now().strftime('%Y%m%d')}.log")

    # Use our Windows-safe handler that gracefully handles locked files
    HandlerClass = WindowsSafeRotatingHandler if sys.platform == "win32" else logging.handlers.RotatingFileHandler
    file_handler = HandlerClass(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(file_handler)
    return logger
