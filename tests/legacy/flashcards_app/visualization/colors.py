from flashcards_app import runtime


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def interpolate_color(start: str, end: str, progress: float) -> str:
    start_rgb = hex_to_rgb(start)
    end_rgb = hex_to_rgb(end)
    ratio = max(0.0, min(1.0, progress))
    mixed = tuple(
        round(start_channel + (end_channel - start_channel) * ratio)
        for start_channel, end_channel in zip(start_rgb, end_rgb)
    )
    return rgb_to_hex(mixed)


def progress_color(value_or_card_id: str | int) -> str:
    if isinstance(value_or_card_id, str):
        progress = runtime.PROGRESS.get(value_or_card_id)
        if progress is None or not progress.read:
            return "#7c8b99"
        value = progress.difficulty
    else:
        value = int(value_or_card_id)
    value = max(1, min(100, value))
    if value < 35:
        return interpolate_color("#e76f51", "#f5b942", (value - 1) / 34)
    if value < 70:
        return interpolate_color("#f5b942", "#69c6a5", (value - 35) / 35)
    return "#69c6a5"


def group_color(card_id: str) -> str:
    for group in runtime.GROUPS:
        if card_id in group.card_ids:
            return group.color
    return "#7c8b99"
