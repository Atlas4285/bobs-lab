"""检查数据, 在内存中抽取英雄并导出策略结果."""

import asyncio
from datetime import UTC, datetime
from os.path import relpath
from pathlib import Path
from uuid import uuid4

from bobs_lab.cli import prompts
from bobs_lab.data_sources import firestone
from bobs_lab.models.hero_stats import HeroStats, TimePeriod
from bobs_lab.models.simulation import SelectionStrategy
from bobs_lab.simulation.evaluation import calculate_results
from bobs_lab.simulation.reporting import save_summary
from bobs_lab.simulation.sampling import draw_heroes
from bobs_lab.utils import logger

RESULT_DIR = Path(__file__).resolve().parents[2] / "result"


def _prepare_data(time_period: TimePeriod) -> bool:
    """检查本地数据并按需更新, 取消时返回 False."""
    logger.info("开始检查本地 Firestone 数据.")
    status = firestone.check_hero_stats(time_period=time_period)
    if not status.is_complete:
        logger.warning(
            "本地数据检查失败: {count} 个文件错误.", count=status.error_count
        )
        asyncio.run(firestone.update_hero_stats(time_period=time_period))
        return True

    logger.success("本地 Firestone 数据检查通过.")
    oldest = status.oldest_update_date
    if oldest is None:
        raise RuntimeError("本地数据缺少更新时间.")
    days = (datetime.now(UTC) - oldest).days
    if days < 1:
        logger.info("全部数据均在最近 24 小时内更新, 跳过刷新.")
        return True

    update = prompts.confirm_update(days)
    if update is None:
        return False
    if update:
        asyncio.run(firestone.update_hero_stats(time_period=time_period))
    return True


def _evaluate(
    datasets: list[HeroStats],
    *,
    iterations: int,
    seed: int | None,
    strategy: SelectionStrategy,
    path: Path,
    metadata: dict[str, str | int | None],
) -> None:
    """每种模式抽取一次并在内存中逐组计算, 导出汇总 Excel."""
    columns: dict[str, dict[int, float | None]] = {}
    for mode in firestone.GAME_MODES:
        groups = [data for data in datasets if data.hero_stats[0].game_mode == mode]
        pools = [{hero.hero_card_id for hero in data.hero_stats} for data in groups]
        hero_ids = sorted(set.intersection(*pools))
        mode_name = "单打" if mode == "battlegrounds" else "双打"
        metadata[f"hero_pool_size/{mode_name}"] = len(hero_ids)
        logger.info(
            "开始抽取英雄. 模式: {mode}, 英雄池 {count} 个, 模拟 {iterations} 轮.",
            mode="单打" if mode == "battlegrounds" else "双打",
            count=len(hero_ids),
            iterations=iterations,
        )
        draws = draw_heroes(hero_ids, game_mode=mode, iterations=iterations, seed=seed)
        for data in groups:
            metadata[f"last_update_date/{mode_name}/mmr-{data.mmr_percentile}"] = (
                data.last_update_date
            )
            results = calculate_results(draws, data, strategy=strategy)
            columns[
                f"模式: {'单打' if mode == 'battlegrounds' else '双打'} / MMR: {data.mmr_percentile}"
            ] = {count: result.average_position for count, result in results.items()}
            del results
        del draws
    save_summary(columns, path, metadata)


def main() -> None:
    """执行交互与模拟流程."""
    time_period = prompts.select_time_period()
    if time_period is None or not _prepare_data(time_period):
        return
    datasets = firestone.load_hero_stats(time_period=time_period)

    iterations = prompts.ask_iterations()
    if iterations is None:
        return
    seed = prompts.ask_seed()
    strategy = prompts.select_strategy()
    if strategy is None:
        return
    run_id = str(uuid4())
    path = RESULT_DIR / f"summary-{run_id[:6]}.xlsx"
    logger.info(
        "本次运行 UUID: {run_id}. 结果文件: {path}.",
        run_id=run_id,
        path=relpath(path),
    )
    metadata: dict[str, str | int | None] = {
        "uuid": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "time_period": time_period,
        "strategy": strategy,
        "iterations": iterations,
        "seed": seed,
        "candidate_counts": "2,4,5,6,7,8",
        "hero_pool": "Intersection across MMR groups for each game mode",
    }
    _evaluate(
        datasets,
        iterations=iterations,
        seed=seed,
        strategy=strategy,
        path=path,
        metadata=metadata,
    )
    logger.success("模拟完成. 结果已保存至 {path}.", path=relpath(path))


if __name__ == "__main__":
    main()
