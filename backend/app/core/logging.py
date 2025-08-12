"""
Logging configuration for the Podcast Generator backend.
"""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """Setup logging configuration."""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with color
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.debug else "INFO",
        colorize=True
    )
    
    # Add file handler for production
    if settings.is_production:
        logger.add(
            "logs/app.log",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="INFO"
        )
    
    # Intercept standard library logging
    class InterceptHandler:
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            frame, depth = sys._getframe(6), 2
            while frame and frame.f_code.co_filename == __file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
    
    # Replace standard logging handlers
    import logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set specific loggers
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("fastapi").handlers = [InterceptHandler()]
    
    logger.info("Logging configured successfully") 