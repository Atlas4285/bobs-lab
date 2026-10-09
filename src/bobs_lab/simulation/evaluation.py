"""根据抽取记录与英雄统计计算选择结果."""

from tqdm import tqdm

from bobs_lab.models.hero_stats import HeroStat, HeroStats
from bobs_lab.models.simulation import HeroDraws, SelectionResult, SelectionStrategy

CANDIDATE_COUNTS = (2, 4, 5, 6, 7, 8)


def calculate_results(
    draws: HeroDraws,
    data: HeroStats,
    *,
    strategy: SelectionStrategy,
) -> dict[int, SelectionResult]:
    """复用每轮候选前缀计算六组结果, 同分时选择靠前的英雄."""
    if strategy not in ("average_position", "pick_rate", "win_rate", "top1_rate"):
        raise ValueError("选择策略无效.")
    if any(hero.game_mode != draws.game_mode for hero in data.hero_stats):
        raise ValueError("英雄统计与抽取记录的游戏模式不一致.")
    heroes = {hero.hero_card_id: hero for hero in data.hero_stats}
    missing = set(draws.hero_ids) - heroes.keys()
    if missing:
        raise ValueError(f"英雄统计缺少抽取池中的英雄: {', '.join(sorted(missing))}.")

    scores = {hero_id: _score(hero, strategy) for hero_id, hero in heroes.items()}
    results = {count: SelectionResult(count, strategy) for count in CANDIDATE_COUNTS}
    for candidates in tqdm(
        draws.rounds, desc="计算选择结果", unit="轮", dynamic_ncols=True
    ):
        for count, result in results.items():
            selected = max(candidates[:count], key=scores.__getitem__)
            result.heroes.append(heroes[selected])
    return results


def _score(hero: HeroStat, strategy: SelectionStrategy) -> float:
    """计算策略分数, 缺失的选取率排在有效值之后."""
    if strategy == "average_position":
        return -hero.average_position
    value = getattr(hero, strategy)
    return value if value is not None else -float("inf")
