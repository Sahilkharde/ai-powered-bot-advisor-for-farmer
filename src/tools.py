"""Langchain tools the agent uses to query mandi price data.

Wraps a pandas-style query over the sample CSV. In production these would
hit the agmarknet scraper / database instead — interface stays the same.
"""
from pathlib import Path
import pandas as pd
from langchain_core.tools import tool

DATA_PATH = Path(__file__).parent.parent / "data" / "sample_mandi_prices.csv"

# Load once at import — fine for demo, swap for a DB connection in prod
_DF = pd.read_csv(DATA_PATH, parse_dates=["date"])


@tool(
    "get_current_prices",
    description=(
        "Get the most recent pomegranate prices in Maharashtra mandis. "
        "Pass a mandi name (Solapur, Sangli, Pune, Nashik, Ahmednagar, Pandharpur) "
        "or 'all' for every mandi. Returns latest modal, min, and max prices in "
        "Rs per quintal, plus arrivals data."
    ),
)
def get_current_prices(mandi: str = "all") -> str:
    """Get the most recent pomegranate prices."""
    latest_date = _DF["date"].max()
    snap = _DF[_DF["date"] == latest_date]
    if mandi.lower() != "all":
        snap = snap[snap["market"].str.lower() == mandi.lower()]
        if snap.empty:
            return f"No price data found for mandi '{mandi}'."

    lines = [f"Pomegranate prices on {latest_date.date()} (Rs/quintal):"]
    for _, r in snap.iterrows():
        lines.append(
            f"- {r['market']}: modal Rs {r['modal_price']:,} "
            f"(range Rs {r['min_price']:,}–{r['max_price']:,}), "
            f"arrivals {r['arrivals_quintals']} quintals"
        )
    return "\n".join(lines)


@tool(
    "get_price_trend",
    description=(
        "Get the price trend for a specific Maharashtra pomegranate mandi over "
        "the last N trading days. Returns average price, percentage change from "
        "start to end of window, and trend direction (rising, falling, or flat). "
        "Default window is 14 days."
    ),
)
def get_price_trend(mandi: str, days: int = 14) -> str:
    """Get the price trend for a specific mandi over the last N days."""
    sub = _DF[_DF["market"].str.lower() == mandi.lower()].sort_values("date")
    if sub.empty:
        return f"No data for mandi '{mandi}'."

    recent = sub.tail(days)
    if len(recent) < 2:
        return f"Not enough data points for {mandi}."

    avg = recent["modal_price"].mean()
    first = recent.iloc[0]["modal_price"]
    last = recent.iloc[-1]["modal_price"]
    pct = ((last - first) / first) * 100
    direction = "rising" if pct > 1 else "falling" if pct < -1 else "flat"

    return (
        f"{mandi} pomegranate trend over last {len(recent)} trading days:\n"
        f"- Average modal price: Rs {avg:,.0f}/quintal\n"
        f"- Started at Rs {first:,}, now Rs {last:,} ({pct:+.1f}%)\n"
        f"- Direction: {direction}"
    )


@tool(
    "compare_mandis",
    description=(
        "Compare today's pomegranate prices across all 6 Maharashtra mandis "
        "(Solapur, Sangli, Pune, Nashik, Ahmednagar, Pandharpur), sorted from "
        "highest to lowest modal price. Use this to decide WHERE to sell."
    ),
)
def compare_mandis() -> str:
    """Compare today's prices across all mandis."""
    latest_date = _DF["date"].max()
    snap = _DF[_DF["date"] == latest_date].sort_values("modal_price", ascending=False)

    lines = [f"Today's pomegranate ranking ({latest_date.date()}):"]
    for i, (_, r) in enumerate(snap.iterrows(), 1):
        lines.append(
            f"{i}. {r['market']}: Rs {r['modal_price']:,}/quintal "
            f"(arrivals: {r['arrivals_quintals']} q)"
        )

    top = snap.iloc[0]
    bottom = snap.iloc[-1]
    spread = top["modal_price"] - bottom["modal_price"]
    spread_pct = (spread / bottom["modal_price"]) * 100
    lines.append(
        f"\nSpread: Rs {spread:,}/quintal ({spread_pct:.1f}%) "
        f"between best and worst mandi today."
    )
    return "\n".join(lines)


# Export for the agent to bind
TOOLS = [get_current_prices, get_price_trend, compare_mandis]