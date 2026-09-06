"""Turn raw tool results into plain-language Markdown a non-accountant can read.

Used by the offline RuleProvider so its chat answers read like sentences and
small tables instead of a JSON dump. The real LLM provider does its own phrasing.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date


def money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def qty(v) -> str:
    try:
        f = float(v)
        return f"{f:,.0f}" if f == int(f) else f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def plural(n: int, word: str, suffix: str = "s") -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}{suffix}"


def _fmt_date(s) -> str:
    try:
        return date.fromisoformat(str(s)[:10]).strftime("%b %-d, %Y")
    except ValueError:
        try:
            return date.fromisoformat(str(s)[:10]).strftime("%b %d, %Y")
        except ValueError:
            return str(s)


FORMATTERS: dict[str, Callable[[dict], str]] = {}


def formatter(name: str):
    def deco(fn):
        FORMATTERS[name] = fn
        return fn

    return deco


@formatter("get_profit_loss")
def _pnl(r: dict) -> str:
    rev, exp, net = r.get("revenue", 0), r.get("expenses", 0), r.get("net_profit", 0)
    margin = (net / rev * 100) if rev else 0
    verb = "made a profit" if net >= 0 else "made a loss"
    out = [
        f"Your business **{verb} of {money(abs(net))}**.",
        "",
        f"- Money earned (revenue): **{money(rev)}**",
        f"- Money spent (costs): **{money(exp)}**",
    ]
    if rev:
        out.append(f"- That keeps about **{margin:.0f} cents of every dollar** as profit.")
    big = [ln for ln in r.get("lines", []) if abs(ln.get("balance", 0)) > 0.005]
    if len(big) > 1:
        out += ["", "Breakdown:"]
        for ln in big:
            amount = -ln["balance"] if ln["type"] == "income" else ln["balance"]
            out.append(f"- {ln['name']}: {money(amount)}")
    return "\n".join(out)


@formatter("get_sales_summary")
def _sales(r: dict) -> str:
    return (
        f"Total sales so far: **{money(r.get('revenue', 0))}**. "
        f"After costs, that leaves **{money(r.get('net_profit', 0))}** of profit."
    )


@formatter("get_cash_flow")
def _cash(r: dict) -> str:
    proj = r.get("projected_balance", 0)
    days = r.get("horizon_days", 30)
    out = [
        f"**In {days} days you're projected to have {money(proj)} in the bank.**",
        "",
        f"- Expected to come in: {money(r.get('expected_inflow', 0))}",
        f"- Expected to go out: {money(r.get('expected_outflow', 0))}",
        f"- Starting balance: {money(r.get('opening_bank', 0))}",
    ]
    if r.get("shortfall") or proj < 0:
        out += ["", "⚠️ **That's a shortfall** — you may not have enough to cover what's due. "
                "Consider chasing unpaid invoices or delaying non-urgent payments."]
    elif proj < r.get("expected_outflow", 0) * 0.2:
        out += ["", "⚠️ This is tight — not much of a cushion."]
    return "\n".join(out)


@formatter("get_receivables")
def _ar(r: dict) -> str:
    rows = r.get("invoices", [])
    if not rows:
        return "Nobody owes you money right now — all invoices are paid. 🎉"
    overdue = [x for x in rows if x.get("overdue")]
    out = [f"**{plural(len(rows), 'unpaid invoice')}, {money(r.get('total', 0))} in total.**"]
    if overdue:
        out.append(f"{len(overdue)} of them are **past due**.")
    out += ["", "| Customer | Invoice | Due | Amount |", "|---|---|---|---|"]
    for x in rows[:12]:
        due = _fmt_date(x["due_date"]) + (" ⚠️" if x.get("overdue") else "")
        out.append(f"| {x['customer']} | {x['invoice_number']} | {due} | {money(x['balance'])} |")
    if len(rows) > 12:
        out.append(f"\n…and {len(rows) - 12} more.")
    return "\n".join(out)


@formatter("get_payables")
def _ap(r: dict) -> str:
    rows = r.get("bills", [])
    if not rows:
        return "You don't owe any suppliers right now."
    out = [f"**You owe suppliers {money(r.get('total', 0))} across {plural(len(rows), 'bill')}.**",
           "", "| Supplier | Bill | Due | Amount |", "|---|---|---|---|"]
    for x in rows[:12]:
        due = _fmt_date(x["due_date"]) + (" ⚠️" if x.get("overdue") else "")
        out.append(f"| {x['supplier']} | {x['bill_number']} | {due} | {money(x['balance'])} |")
    if len(rows) > 12:
        out.append(f"\n…and {len(rows) - 12} more.")
    return "\n".join(out)


@formatter("get_inventory_position")
def _inv(r: dict) -> str:
    rows = r.get("products", [])
    if not rows:
        return "No products are being tracked yet."
    low = [x for x in rows if x.get("below_reorder")]
    units = sum(float(x.get("on_hand", 0)) for x in rows)
    value = sum(float(x.get("on_hand", 0)) * float(x.get("avg_cost", 0)) for x in rows)

    out = [
        f"You're tracking **{plural(len(rows), 'product')}**, "
        f"**{qty(units)} units** in stock"
        + (f" worth about **{money(value)}**" if value else "")
        + ".",
    ]
    if low:
        out += ["", f"**{plural(len(low), 'product')} need reordering:**"]
        for x in low:
            out.append(
                f"- **{x['name']}** ({x['sku']}) — {qty(x['on_hand'])} left, "
                f"reorder at {qty(x['reorder_level'])}"
            )
    else:
        out.append("\nEverything is above its reorder level. 🟢")

    out += ["", "| Product | In stock | Reorder at | |", "|---|---:|---:|:--|"]
    for x in sorted(rows, key=lambda r: (not r.get("below_reorder"), r["name"]))[:20]:
        flag = "🔴" if x.get("below_reorder") else "🟢"
        out.append(f"| {x['name']} ({x['sku']}) | {qty(x['on_hand'])} | "
                   f"{qty(x['reorder_level'])} | {flag} |")
    if len(rows) > 20:
        out.append(f"\n…and {len(rows) - 20} more.")
    return "\n".join(out)


@formatter("get_stockout_risk")
def _risk(r: dict) -> str:
    if "at_risk" in r:
        rows = r["at_risk"]
        if not rows:
            return "Good news — **nothing is at risk of running out** in the next 30 days."
        out = [f"**{plural(len(rows), 'product')} could run out soon:**", ""]
        for x in rows:
            out.append(
                f"- **{x.get('name', x.get('sku'))}** — {qty(x.get('on_hand'))} in stock, "
                f"about {qty(x.get('forecast_qty'))} needed over the next "
                f"{x.get('horizon_days', 30)} days"
                + (f", {x['lead_time_days']}-day supplier lead time" if x.get("lead_time_days") else "")
                + (f". Suggested order: ~{qty(x['suggested_order_qty'])} units"
                   if x.get("suggested_order_qty") else "")
            )
        return "\n".join(out)
    level = r.get("risk", "unknown")
    label = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟢 Low",
             "none": "No"}.get(level, level)
    out = [f"**Stockout risk: {label}.**", "",
           f"- In stock now: {qty(r.get('on_hand'))}",
           f"- Expected demand ({r.get('horizon_days', 30)} days): {qty(r.get('forecast_qty'))}",
           f"- Days of cover left: {r.get('days_of_cover', '?')}"]
    if r.get("suggested_order_qty", 0) > 0:
        out.append(f"\n👉 Consider ordering about **{qty(r['suggested_order_qty'])} units**.")
    return "\n".join(out)


@formatter("get_demand_forecast")
def _demand(r: dict) -> str:
    return (
        f"Expected demand over the next **{r.get('horizon_days', 30)} days**: "
        f"about **{qty(r.get('forecast_qty'))} units** "
        f"(~{qty(r.get('avg_daily_demand'))} per day, based on {r.get('history_days', 0)} "
        f"days of history)."
    )


@formatter("get_supplier_performance")
def _suppliers(r: dict) -> str:
    out = ["**Your suppliers:**", "", "| Supplier | Lead time | Reliability | Payment terms |",
           "|---|---|---|---|"]
    for s in r.get("suppliers", []):
        out.append(f"| {s['name']} | {s['lead_time_days']} days | "
                   f"{float(s['reliability']) * 100:.0f}% | {s['payment_terms_days']} days |")
    anomalies = r.get("price_anomalies", [])
    if anomalies:
        out += ["", "**Unusual price changes:**"]
        for a in anomalies:
            out.append(f"- {a['supplier']} quoted {money(a['unit_cost'])} for {a['product']} "
                       f"({a['pct_change']:+.0f}% vs their usual {money(a['baseline_avg'])})")
    else:
        out += ["", "No unusual price changes detected."]
    return "\n".join(out)


@formatter("get_recommendations")
def _recs(r: dict) -> str:
    rows = r.get("recommendations", [])
    if not rows:
        return "Nothing needs your attention right now."
    icon = {"high": "🔴", "medium": "🟠", "low": "🔵", "info": "⚪"}
    out = [f"**{plural(len(rows), 'thing')} worth a look:**", ""]
    for i, x in enumerate(rows, 1):
        out.append(f"{i}. {icon.get(x['severity'], '•')} **{x['title']}** — {x['description']}"
                   + (f" _(impact: {x['estimated_impact']})_" if x.get("estimated_impact") else ""))
    return "\n".join(out)


@formatter("get_production_plan")
def _production(r: dict) -> str:
    orders = r.get("orders", [])
    if not orders:
        return "No production orders are open right now."
    out = [f"**{plural(len(orders), 'production order')} in progress:**", ""]
    for o in orders:
        line = f"- **{o['product']}** ({o['number']}) — make {qty(o['quantity'])}, status: {o['status']}"
        short = o.get("shortfalls", [])
        if short:
            names = ", ".join(f"{s['name']} (short {qty(s['shortfall'])})" for s in short)
            line += f"\n  ⚠️ Not enough materials: {names}"
        out.append(line)
    return "\n".join(out)


@formatter("get_trial_balance")
def _tb(r: dict) -> str:
    rows = [a for a in r.get("accounts", []) if abs(a.get("balance", 0)) > 0.005]
    out = ["**Account balances:**", "", "| Account | Balance |", "|---|---|"]
    for a in rows:
        out.append(f"| {a['code']} {a['name']} | {money(a['balance'])} |")
    return "\n".join(out)


def humanize(name: str, result: dict) -> str:
    if isinstance(result, dict) and result.get("error"):
        return f"I couldn't get that: {result['error']}"
    fn = FORMATTERS.get(name)
    if fn:
        try:
            return fn(result)
        except Exception:  # noqa: BLE001 - fall back to a generic rendering
            pass
    # generic key/value fallback
    if isinstance(result, dict):
        lines = []
        for k, v in result.items():
            if isinstance(v, (dict, list)):
                continue
            label = k.replace("_", " ").capitalize()
            lines.append(f"- {label}: **{money(v) if 'cost' in k or 'total' in k or 'balance' in k or 'revenue' in k or 'profit' in k else v}**")
        if lines:
            return "\n".join(lines)
    return f"```\n{result}\n```"


def narrate(results: list[dict]) -> str:
    """Compose the final chat answer from one or more tool results."""
    if not results:
        return ""
    blocks = []
    for r in results:
        body = humanize(r["name"], r.get("result", {}))
        blocks.append(body if len(results) == 1 else body)
    answer = "\n\n".join(blocks)
    answer += "\n\n_These figures come straight from your accounting and inventory records._"
    return answer
