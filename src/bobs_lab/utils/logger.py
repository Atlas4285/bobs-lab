"""全局日志工具."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger as _logger

if TYPE_CHECKING:
    from loguru import HandlerConfig


class Logger:
    """配置并代理 Loguru 的全局日志实例."""

    FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{file.name}</cyan>:<cyan>{line}</cyan> | "
        "<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )

    def __init__(self, *, level: str = "INFO", log_file: str | Path | None = None):
        """初始化全局日志配置."""
        self.configure(level=level, log_file=log_file)

    def configure(
        self, *, level: str = "INFO", log_file: str | Path | None = None
    ) -> None:
        """设置日志等级与可选文件输出."""
        handlers: list[HandlerConfig] = [
            {
                "sink": sys.stderr,
                "level": level,
                "format": self.FORMAT,
                "diagnose": False,
                "backtrace": False,
            }
        ]
        if log_file is not None:
            handlers.append(
                {
                    "sink": Path(log_file),
                    "level": level,
                    "format": self.FORMAT,
                    "encoding": "utf-8",
                    "colorize": False,
                    "diagnose": False,
                    "backtrace": False,
                }
            )
        _logger.configure(handlers=handlers)

    def __getattr__(self, name: str) -> Any:
        """代理日志方法并保留调用位置."""
        return getattr(_logger, name)


logger = Logger()


def main() -> None:
    """输出各日志等级的样式示例."""
    logger.configure(level="TRACE")
    logger.trace("样式测试: TRACE.")
    logger.debug("样式测试: DEBUG.")
    logger.info("样式测试: INFO.")
    logger.success("样式测试: SUCCESS.")
    logger.warning("样式测试: WARNING.")
    logger.error("样式测试: ERROR.")
    logger.critical("样式测试: CRITICAL.")


if __name__ == "__main__":
    main()
