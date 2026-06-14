import sys
from pathlib import Path

from loguru import logger as _logger


def _configure_logger(log_dir: Path | None = None) -> None:
    _logger.remove()

    _logger.add(
        sys.stderr,
        level="DEBUG",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
        ),
        colorize=True,
    )

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_dir / "obs_{time:YYYY-MM-DD}.log",
            level="INFO",
            rotation="1 day",
            retention="30 days",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
        )


_configure_logger()

log = _logger.bind()
