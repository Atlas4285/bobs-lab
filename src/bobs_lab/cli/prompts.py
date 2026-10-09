"""命令行参数选择与输入."""

import questionary
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent, merge_key_bindings

from bobs_lab.models.hero_stats import TimePeriod
from bobs_lab.models.simulation import SelectionStrategy

STYLE = questionary.Style(
    [
        ("pointer", "fg:#00afff bold"),
        ("highlighted", "fg:#00afff bold"),
        ("selected", ""),
        ("answer", "fg:#00afff bold"),
    ]
)


def select_time_period() -> TimePeriod | None:
    """选择统计时间窗口, 默认最新补丁."""
    choices: dict[str, TimePeriod] = {
        "最新补丁": "last-patch",
        "最近 3 天": "past-three",
        "最近 7 天": "past-seven",
        "最近 30 天": "all-time",
    }
    answer = _select("请选择统计时间窗口:", list(choices))
    return choices[answer] if answer is not None else None


def confirm_update(days: int) -> bool | None:
    """询问是否刷新本地数据, 默认不更新."""
    answer = _select(f"本地数据最早更新于 {days} 天前, 是否刷新?", ["不更新", "更新"])
    return answer == "更新" if answer is not None else None


def ask_iterations() -> int | None:
    """输入模拟次数, 默认一百万次."""
    return _integer(
        "请输入模拟次数 (默认 1M):", default=1_000_000, positive=True, initial="1M"
    )


def ask_seed() -> int | None:
    """输入随机种子, 默认 42, 清空输入表示完全随机."""
    return _integer(
        "请输入随机种子 (默认 42, 清空表示完全随机):",
        default=None,
        positive=False,
        initial=42,
    )


def select_strategy() -> SelectionStrategy | None:
    """选择策略, 默认平均排名优先."""
    choices: dict[str, SelectionStrategy] = {
        "平均排名优先": "average_position",
        "选取率优先": "pick_rate",
        "胜率优先 (单人前四, 双人前二)": "win_rate",
        "第一率优先": "top1_rate",
    }
    answer = _select("请选择英雄选择策略:", list(choices))
    return choices[answer] if answer is not None else None


def _select(message: str, choices: list[str]) -> str | None:
    """使用箭头选择, Enter 确认."""
    return _ask(
        questionary.select(
            message,
            choices=choices,
            instruction="(上下箭头选择, Enter 确认, Esc 退出)",
            style=STYLE,
        )
    )


def _integer(
    message: str,
    *,
    default: int | None,
    positive: bool,
    initial: int | str | None = None,
) -> int | None:
    """输入整数, 留空使用默认值, 取消时退出."""

    def validate(text: str) -> bool | str:
        """校验整数输入."""
        if not text.strip():
            return True
        try:
            value = _parse_integer(text, allow_suffix=positive)
        except ValueError:
            return "请输入整数."
        return "请输入大于 0 的整数." if positive and value <= 0 else True

    answer = _ask(
        questionary.text(
            message,
            default=str(initial) if initial is not None else "",
            validate=validate,
            instruction="(Enter 确认, Esc 退出)",
            style=STYLE,
        )
    )
    if answer is None:
        raise SystemExit(0)
    return _parse_integer(answer, allow_suffix=positive) if answer.strip() else default


def _parse_integer(text: str, *, allow_suffix: bool) -> int:
    """解析整数, 模拟次数支持 K 和 M 后缀."""
    value = text.strip()
    if allow_suffix and value[-1:].upper() in ("K", "M"):
        multiplier = 1_000 if value[-1].upper() == "K" else 1_000_000
        return int(value[:-1]) * multiplier
    return int(value)


def _ask(question: questionary.Question) -> str | None:
    """执行交互, Esc 或默认中止操作返回空值."""
    exit_keys = KeyBindings()

    @exit_keys.add("escape", eager=True)
    def exit_prompt(event: KeyPressEvent) -> None:
        """退出当前交互."""
        event.app.exit(result=None)

    existing_keys = question.application.key_bindings
    question.application.key_bindings = merge_key_bindings(
        [existing_keys, exit_keys] if existing_keys is not None else [exit_keys]
    )
    return question.ask()
