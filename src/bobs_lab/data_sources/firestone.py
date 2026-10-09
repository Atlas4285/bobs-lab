"""Firestone 数据获取, 检查与加载."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import requests
from tqdm import tqdm

from bobs_lab.models.data_status import DataStatus, FileStatus
from bobs_lab.models.hero_stats import GameMode, HeroStats, MmrPercentile, TimePeriod
from bobs_lab.utils import logger

BASE_URL = "https://static.zerotoheroes.com/api/bgs"
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
GAME_MODES: tuple[GameMode, ...] = get_args(GameMode.__value__)
MMR_PERCENTILES: tuple[MmrPercentile, ...] = get_args(MmrPercentile.__value__)


async def fetch_hero_stats(
    *,
    time_period: TimePeriod = "last-patch",
    data_dir: str | Path = DATA_DIR,
    timeout: float = 30,
) -> None:
    """并发获取全部十组数据并保存原始 JSON, 失败时抛出异常."""
    groups = _groups(time_period, data_dir)
    if timeout <= 0:
        raise ValueError("请求超时必须大于 0.")
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()
    with (
        ThreadPoolExecutor(max_workers=len(groups)) as executor,
        tqdm(
            total=len(groups), desc="更新 Firestone 数据", unit="组", dynamic_ncols=True
        ) as progress,
    ):

        async def fetch_one(mode: GameMode, mmr: MmrPercentile, path: Path) -> None:
            """在线程池执行一组请求并更新进度."""
            mode_path = "/duo" if mode == "battlegrounds-duo" else ""
            url = (
                f"{BASE_URL}{mode_path}/hero-stats/mmr-{mmr}/{time_period}/"
                "overview-from-hourly.gz.json"
            )
            try:
                await loop.run_in_executor(executor, _download, url, path, timeout)
            finally:
                progress.update(1)

        results = await asyncio.gather(
            *(fetch_one(mode, mmr, path) for mode, mmr, path in groups),
            return_exceptions=True,
        )
    for result in results:
        if isinstance(result, BaseException):
            raise result


async def update_hero_stats(
    *,
    time_period: TimePeriod = "last-patch",
    data_dir: str | Path = DATA_DIR,
    timeout: float = 30,
) -> DataStatus:
    """获取全部数据后重新检查, 仍有错误时抛出异常."""
    logger.info("开始更新数据.")
    await fetch_hero_stats(time_period=time_period, data_dir=data_dir, timeout=timeout)
    logger.info("开始检查本地 Firestone 数据.")
    status = check_hero_stats(time_period=time_period, data_dir=data_dir)
    if not status.is_complete:
        details = "; ".join(
            f"{file.path.name}: {file.error}"
            for file in status.files
            if not file.is_valid
        )
        raise RuntimeError(
            f"更新后的 Firestone 数据检查失败: {status.error_count} 个文件错误. {details}"
        )
    logger.success("更新后的 Firestone 数据检查通过.")
    return status


def check_hero_stats(
    *, time_period: TimePeriod = "last-patch", data_dir: str | Path = DATA_DIR
) -> DataStatus:
    """检查全部预期文件的可读性, 必要数据与更新时间."""
    files = []
    for mode, mmr, path in _groups(time_period, data_dir):
        date = None
        error = None
        try:
            data = _load(path, mode, mmr, time_period)
            date = datetime.fromisoformat(data.last_update_date)
            if date.tzinfo is None:
                raise ValueError("数据更新时间缺少时区.")
            date = date.astimezone(UTC)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            error = str(exc)
        files.append(FileStatus(path=path, last_update_date=date, error=error))
    return DataStatus(files=files)


def load_hero_stats(
    *, time_period: TimePeriod = "last-patch", data_dir: str | Path = DATA_DIR
) -> list[HeroStats]:
    """加载全部十组英雄统计, 失败时抛出异常."""
    return [
        _load(path, mode, mmr, time_period)
        for mode, mmr, path in _groups(time_period, data_dir)
    ]


def _groups(
    time_period: TimePeriod, data_dir: str | Path
) -> list[tuple[GameMode, MmrPercentile, Path]]:
    """生成全部预期分组及文件路径."""
    if time_period not in get_args(TimePeriod.__value__):
        raise ValueError("统计时间窗口无效.")
    return [
        (
            mode,
            mmr,
            Path(data_dir) / f"firestone-{mode}-mmr-{mmr}-{time_period}.json",
        )
        for mode in GAME_MODES
        for mmr in MMR_PERCENTILES
    ]


def _download(url: str, path: Path, timeout: float) -> None:
    """请求一组数据并保留原始 JSON 内容."""
    with requests.get(url, timeout=timeout) as response:
        response.raise_for_status()
        response.json()
        path.write_bytes(response.content)


def _load(
    path: Path, mode: GameMode, mmr: MmrPercentile, time_period: TimePeriod
) -> HeroStats:
    """加载一组统计并确认英雄数据非空."""
    data = HeroStats.load(
        path, game_mode=mode, mmr_percentile=mmr, time_period=time_period
    )
    if not data.hero_stats:
        raise ValueError("英雄统计为空.")
    return data
