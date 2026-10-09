"""随机抽取英雄候选."""

import random

from tqdm import tqdm

from bobs_lab.models.hero_stats import GameMode
from bobs_lab.models.simulation import HeroDraws


def draw_heroes(
    hero_ids: list[str],
    *,
    game_mode: GameMode,
    iterations: int,
    seed: int | None = None,
) -> HeroDraws:
    """每轮无重复抽取八个英雄, 保留顺序供后续计算复用."""
    if game_mode not in ("battlegrounds", "battlegrounds-duo"):
        raise ValueError("游戏模式无效.")
    if type(iterations) is not int or iterations <= 0:
        raise ValueError("模拟次数必须为正整数.")
    if len(hero_ids) < 8:
        raise ValueError("英雄池至少需要 8 个英雄.")
    if len(set(hero_ids)) != len(hero_ids):
        raise ValueError("英雄编号不能重复.")

    pool = list(hero_ids)
    rng = random.Random(seed)
    rounds = [
        tuple(rng.sample(pool, 8))
        for _ in tqdm(
            range(iterations), desc="随机抽取英雄", unit="轮", dynamic_ncols=True
        )
    ]
    return HeroDraws(game_mode=game_mode, hero_ids=pool, rounds=rounds, seed=seed)
