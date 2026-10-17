"""Presentation helpers for the Simulator page (layout and wording only, no calculations)."""
import html
import streamlit as st

# strategy names and one-line descriptions, in the order the advisors are offered
ADVISORS = {
    "always_cash": ("Always Cash", "Sells all stocks on the first day and holds cash, a no-risk baseline."),
    "always_hold": ("Always Hold", "Keeps the starting shares for the whole period without trading."),
    "dory": ("Dory", "Each day, moves everything into the stock that rose most from open to close, or into cash "
                     "if none rose. It reacts to past moves, so it isn't a prediction."),
}

# validated categorical slots (light, dark) for the allocation bar; cash uses a neutral gray
SERIES_COLORS = [("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"), ("#eda100", "#c98500"),
                 ("#e87ba4", "#d55181"), ("#008300", "#008300"), ("#6250d6", "#9085e9"), ("#e34948", "#e66767")]
CASH_COLOR = ("#a3a29c", "#6b6a65")


def strategy_colors():
    """A fixed color per strategy (the first validated categorical slots), so a strategy keeps its color."""
    dark = is_dark_theme()
    return {name: (SERIES_COLORS[i][1] if dark else SERIES_COLORS[i][0])
            for i, (name, _) in enumerate(ADVISORS.values())}


def advisor_name(advisor):
    return ADVISORS.get(advisor, (advisor, ""))[0]


def is_dark_theme():
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def format_date(d):
    return f"{d:%b} {d.day}, {d.year}"


def format_range(start, end):
    if start.year == end.year:
        return f"{start:%b} {start.day} – {format_date(end)}"
    return f"{format_date(start)} – {format_date(end)}"


def period_label(weeks):
    return f"Last {weeks} week{'' if weeks == 1 else 's'}"


def _color(index, ticker, dark):
    pair = CASH_COLOR if ticker == "Cash" else SERIES_COLORS[index % len(SERIES_COLORS)]
    return pair[1] if dark else pair[0]


def allocation_bar(allocations):
    """A single stacked bar of the allocation percentages, with a text legend (the values are always labeled)."""
    dark = is_dark_theme()
    parts = [(t, p) for t, p in allocations.items()]
    stock_index = {t: i for i, t in enumerate(t for t, _ in parts if t != "Cash")}
    segments = "".join(
        f'<div title="{html.escape(t)}: {p}%" style="flex:{p} 0 0;min-width:4px;background:'
        f'{_color(stock_index.get(t, 0), t, dark)};"></div>'
        for t, p in parts if p > 0)
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:16px;white-space:nowrap;">'
        f'<span style="width:10px;height:10px;border-radius:3px;background:{_color(stock_index.get(t, 0), t, dark)};">'
        f'</span>{html.escape(t)} {p}%</span>'
        for t, p in parts)
    st.markdown(
        f'<div role="img" aria-label="Allocation: {html.escape(", ".join(f"{t} {p}%" for t, p in parts))}" '
        f'style="display:flex;gap:2px;height:12px;border-radius:4px;overflow:hidden;margin:4px 0 8px;">'
        f'{segments}</div><div style="font-size:0.9rem;line-height:1.8;">{legend}</div>',
        unsafe_allow_html=True)


def strategy_list(selected_advisors):
    lines = []
    for advisor, (name, description) in ADVISORS.items():
        if advisor in selected_advisors:
            lines.append(f":material/check_circle: **{name}**: {description}")
        else:
            lines.append(f":gray[:material/radio_button_unchecked: **{name}** (not selected): {description}]")
    st.markdown("\n\n".join(lines))


def join_words(words):
    """["1", "4", "26"] -> "1, 4 and 26"."""
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"
