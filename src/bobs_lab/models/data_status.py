"""本地数据文件的检查结果."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileStatus:
    """单个文件的检查结果."""

    path: Path  # 文件路径.
    last_update_date: datetime | None = None  # API 数据更新时间.
    error: str | None = None  # 检查失败原因.

    @property
    def is_valid(self) -> bool:
        """文件是否通过检查."""
        return self.error is None and self.last_update_date is not None


@dataclass(frozen=True, slots=True)
class DataStatus:
    """全部预期文件的检查结果, 包含缺失文件的记录."""

    files: list[FileStatus]  # 各预期文件的检查结果.

    @property
    def is_complete(self) -> bool:
        """检查记录是否非空, 无重复且全部有效."""
        return (
            bool(self.files)
            and len({file.path for file in self.files}) == len(self.files)
            and all(file.is_valid for file in self.files)
        )

    @property
    def error_count(self) -> int:
        """未通过检查的文件数量."""
        return sum(not file.is_valid for file in self.files)

    @property
    def oldest_update_date(self) -> datetime | None:
        """有效文件中最早的数据更新时间."""
        return min(
            (
                file.last_update_date
                for file in self.files
                if file.is_valid and file.last_update_date is not None
            ),
            default=None,
        )
