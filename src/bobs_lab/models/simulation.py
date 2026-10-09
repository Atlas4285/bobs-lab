"""英雄抽取与策略计算结果模型."""

from dataclasses import dataclass, field
from typing import Literal

from .hero_stats import GameMode, HeroStat

type SelectionStrategy = Literal[
    "average_position", "pick_rate", "win_rate", "top1_rate"
]


@dataclass(slots=True)
class HeroDraws:
    """一个模式下的英雄池与逐轮抽取记录."""

    game_mode: GameMode  # 抽取所属模式.
    hero_ids: list[str]  # 抽取使用的完整英雄池.
    rounds: list[tuple[str, ...]]  # 每轮八个英雄编号, 保留随机顺序.
    seed: int | None  # 随机种子, 空值表示完全随机.

    @property
    def iterations(self) -> int:
        """已完成的抽取次数."""
        return len(self.rounds)


@dataclass(slots=True)
class SelectionResult:
    """一个候选数量与策略下的逐轮选择结果."""

    candidate_count: int  # 每轮候选英雄数量.
    strategy: SelectionStrategy  # 英雄选择策略.
    heroes: list[HeroStat] = field(default_factory=list)  # 每轮选中的英雄统计.

    @property
    def iterations(self) -> int:
        """已完成的计算轮次."""
        return len(self.heroes)

    @property
    def average_position(self) -> float | None:
        """全部轮次的平均排名."""
        if not self.heroes:
            return None
        return sum(hero.average_position for hero in self.heroes) / self.iterations

    @property
    def average_position_history(self) -> list[float]:
        """截至每轮的累计平均排名."""
        history = []
        total = 0.0
        for iteration, hero in enumerate(self.heroes, start=1):
            total += hero.average_position
            history.append(total / iteration)
        return history

    @property
    def placement_distribution(self) -> dict[int, float]:
        """各轮英雄名次分布的等权平均概率."""
        totals: dict[int, float] = {}
        for hero in self.heroes:
            for placement in hero.placement_distribution:
                totals[placement.rank] = (
                    totals.get(placement.rank, 0.0) + placement.rate
                )
        return {rank: total / self.iterations for rank, total in sorted(totals.items())}
