"""英雄统计与数据分组模型."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

type MmrPercentile = Literal[100, 50, 25, 10, 1]
type TimePeriod = Literal["last-patch", "past-three", "past-seven", "all-time"]
type GameMode = Literal["battlegrounds", "battlegrounds-duo"]


@dataclass(frozen=True, slots=True)
class PlacementStat:
    """最终名次的概率."""

    rank: int  # 最终名次.
    percentage: float  # 取得该名次的百分比.

    @property
    def rate(self) -> float:
        """取得该名次的概率."""
        return self.percentage / 100


@dataclass(frozen=True, slots=True)
class HeroStat:
    """策略计算所需的单个英雄统计."""

    hero_card_id: str  # 英雄卡牌编号.
    game_mode: GameMode  # 游戏模式.
    mmr_percentile: MmrPercentile  # 英雄统计所属的 MMR 分位.
    time_period: TimePeriod  # 英雄统计的时间窗口.
    average_position: float  # 平均最终名次.
    total_offered: int  # 被提供的次数.
    total_picked: int  # 被选择的次数.
    placement_distribution: list[PlacementStat]  # 最终名次分布.

    @property
    def pick_rate(self) -> float | None:
        """被提供时的选择概率."""
        return self.total_picked / self.total_offered if self.total_offered else None

    @property
    def top1_rate(self) -> float:
        """整局第一名概率."""
        return sum(item.rate for item in self.placement_distribution if item.rank == 1)

    @property
    def win_rate(self) -> float:
        """按英雄所属模式计算胜率."""
        if self.game_mode == "battlegrounds":
            winning_rank = 4
        elif self.game_mode == "battlegrounds-duo":
            winning_rank = 2
        else:
            raise ValueError("游戏模式必须为 battlegrounds 或 battlegrounds-duo.")
        return sum(
            item.rate
            for item in self.placement_distribution
            if 1 <= item.rank <= winning_rank
        )


@dataclass(frozen=True, slots=True)
class HeroStats:
    """指定 MMR 分位和时间窗口下的全部英雄统计."""

    hero_stats: list[HeroStat]  # 全部英雄统计.
    mmr_percentile: MmrPercentile  # 本份数据所属的 MMR 分位.
    time_period: TimePeriod  # 本份数据的统计时间窗口.
    last_update_date: str  # API 数据更新时间.

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        game_mode: GameMode,
        mmr_percentile: MmrPercentile | None = None,
        time_period: TimePeriod | None = None,
    ) -> Self:
        """从 JSON 数据提取所需字段并绑定分组信息."""
        if not isinstance(data, dict):
            raise TypeError("英雄统计的顶层必须是对象.")
        values = _snake_keys(data)
        raw_heroes = [_snake_keys(item) for item in values["hero_stats"]]
        first = raw_heroes[0] if raw_heroes else {}
        source_mmr = values.get("mmr_percentile", first.get("mmr_percentile"))
        source_period = values.get("time_period", first.get("time_period"))
        mmr_percentile = mmr_percentile if mmr_percentile is not None else source_mmr
        time_period = time_period if time_period is not None else source_period
        if game_mode not in ("battlegrounds", "battlegrounds-duo"):
            raise ValueError("游戏模式无效.")
        if mmr_percentile not in (100, 50, 25, 10, 1):
            raise ValueError("数据缺少有效的 MMR 分位.")
        if time_period not in ("last-patch", "past-three", "past-seven", "all-time"):
            raise ValueError("数据缺少有效的时间窗口.")
        if "game_mode" in values and values["game_mode"] != game_mode:
            raise ValueError("数据的游戏模式不一致.")
        if source_mmr is not None and source_mmr != mmr_percentile:
            raise ValueError("数据的 MMR 分位不一致.")
        if source_period is not None and source_period != time_period:
            raise ValueError("数据的时间窗口不一致.")
        for item in raw_heroes:
            if item.get("game_mode", game_mode) != game_mode:
                raise ValueError("英雄统计的游戏模式不一致.")
            if (
                item.get("mmr_percentile", values.get("mmr_percentile"))
                != mmr_percentile
                or item.get("time_period", values.get("time_period")) != time_period
            ):
                raise ValueError("英雄统计属于不同分位或时间窗口.")
        heroes = [
            HeroStat(
                hero_card_id=item["hero_card_id"],
                game_mode=game_mode,
                mmr_percentile=mmr_percentile,
                time_period=time_period,
                average_position=item["average_position"],
                total_offered=item["total_offered"],
                total_picked=item["total_picked"],
                placement_distribution=[
                    PlacementStat(
                        rank=placement["rank"], percentage=placement["percentage"]
                    )
                    for placement in item["placement_distribution"]
                ],
            )
            for item in raw_heroes
        ]
        return cls(
            hero_stats=heroes,
            mmr_percentile=mmr_percentile,
            time_period=time_period,
            last_update_date=values["last_update_date"],
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        game_mode: GameMode,
        mmr_percentile: MmrPercentile | None = None,
        time_period: TimePeriod | None = None,
    ) -> Self:
        """读取统计文件并绑定所属模式与分组."""
        return cls.from_dict(
            json.loads(Path(path).read_text(encoding="utf-8")),
            game_mode=game_mode,
            mmr_percentile=mmr_percentile,
            time_period=time_period,
        )


def _snake_keys(data: dict[str, Any]) -> dict[str, Any]:
    """将字段名转换为蛇形命名."""
    return {
        re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower(): value
        for key, value in data.items()
    }
