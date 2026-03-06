import logging
import sys

from loguru import logger

from app.config import settings


class _InterceptHandler(logging.Handler):
    """Route stdlib logging (uvicorn, sqlalchemy) through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru for the application.

    - Development: colourised, human-readable output on stdout.
    - Production: structured JSON on stdout (ready for log aggregators).

    stdlib logging (uvicorn access logs, SQLAlchemy, etc.) is intercepted and
    forwarded to loguru so there is a single logging pipeline.
    """
    logger.remove()

    if settings.app_env == "production":
        logger.add(sys.stdout, level="INFO", serialize=True)
    else:
        logger.add(
            sys.stdout,
            level="DEBUG",
            colorize=True,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
        )

    # Forward all stdlib log records into loguru.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
