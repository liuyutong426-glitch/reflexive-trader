"""ReflexiveTrader Pro — 模块3: Notion Alpha Log Integration"""

from __future__ import annotations

from notion_client import Client

from config import get_notion_api_key, load_config, save_config
from models import TradePlan
from utils import calc_r_multiple, console


# ── Notion 数据库 Schema 定义 ────────────────────────────────────

DB_PROPERTIES = {
    "Ticker": {"title": {}},
    "Direction": {"select": {"options": [
        {"name": "LONG"}, {"name": "SHORT"},
        {"name": "REDUCE_LONG"}, {"name": "REDUCE_SHORT"},
    ]}},
    "Entry Price": {"number": {"format": "dollar"}},
    "Position %": {"number": {"format": "percent"}},
    "Profit Target": {"number": {"format": "dollar"}},
    "Risk Reward": {"number": {"format": "number"}},
    "Win Rate": {"number": {"format": "percent"}},
    "Price Stop": {"number": {"format": "dollar"}},
    "Time Stop": {"date": {}},
    "Logic Stop": {"rich_text": {}},
    "Entry Emotion": {
        "select": {
            "options": [
                {"name": "confident", "color": "green"},
                {"name": "calm", "color": "blue"},
                {"name": "exploratory", "color": "purple"},
                {"name": "fearful", "color": "red"},
                {"name": "fomo", "color": "orange"},
                {"name": "fatigued", "color": "yellow"},
            ]
        }
    },
    "Familiarity": {"number": {"format": "number"}},
    "Technical Confirmed": {"checkbox": {}},
    "Thesis": {"rich_text": {}},
    "Known Factors": {"rich_text": {}},
    "Unknown Factors": {"rich_text": {}},
    "Priced In": {"rich_text": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "PLANNED", "color": "gray"},
                {"name": "ACTIVE", "color": "blue"},
                {"name": "CLOSED", "color": "green"},
            ]
        }
    },
    "Actual Exit": {"number": {"format": "dollar"}},
    "Actual Return %": {"number": {"format": "percent"}},
    "R Multiple": {"number": {"format": "number"}},
    "Deviation %": {"number": {"format": "percent"}},
    "Psych Notes": {"rich_text": {}},
}


# ── 辅助函数 ─────────────────────────────────────────────────────

def _get_client(cfg: dict) -> Client:
    return Client(auth=get_notion_api_key(cfg))


def _rich_text(text: str) -> list[dict]:
    return [{"text": {"content": text[:2000]}}] if text else []


def _title_text(text: str) -> list[dict]:
    return [{"text": {"content": text}}]


# ── 自动创建数据库 ───────────────────────────────────────────────

def ensure_database(cfg: dict | None = None) -> tuple[Client, str]:
    """确保 Notion 数据库存在，不存在则自动创建。返回 (client, database_id)。"""
    if cfg is None:
        cfg = load_config()

    client = _get_client(cfg)
    db_id = cfg.get("notion", {}).get("database_id", "")

    if db_id:
        return client, db_id

    parent_page_id = cfg.get("notion", {}).get("parent_page_id", "")
    if not parent_page_id or parent_page_id == "xxx":
        raise ValueError("请在 config.yaml 中设置 notion.parent_page_id")

    console.print("[muted]首次运行，正在创建 Notion 数据库...[/muted]")
    response = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "ReflexiveTrader Alpha Log"}}],
        properties=DB_PROPERTIES,
    )
    db_id = response["id"]
    cfg["notion"]["database_id"] = db_id
    save_config(cfg)
    console.print(f"[profit]Notion 数据库已创建: {db_id}[/profit]")
    return client, db_id


# ── CRUD 操作 ────────────────────────────────────────────────────

def sync_trade_plan(plan: TradePlan) -> str:
    """将交易计划同步到 Notion，返回 page_id。"""
    client, db_id = ensure_database()
    h = plan.hypothesis
    inv = plan.invalidation
    psy = plan.psychology
    pos = plan.position

    properties = {
        "Ticker": {"title": _title_text(h.ticker)},
        "Direction": {"select": {"name": h.direction}},
        "Entry Price": {"number": pos.entry_price},
        "Position %": {"number": pos.position_pct / 100},
        "Profit Target": {"number": inv.profit_target_1},
        "Risk Reward": {"number": pos.risk_reward},
        "Win Rate": {"number": pos.win_rate},
        "Price Stop": {"number": inv.price_stop},
        "Logic Stop": {"rich_text": _rich_text(inv.logic_stop)},
        "Entry Emotion": {"select": {"name": psy.emotion}},
        "Familiarity": {"number": h.familiarity_score},
        "Technical Confirmed": {"checkbox": h.technical_confirmed},
        "Thesis": {"rich_text": _rich_text(h.thesis)},
        "Known Factors": {"rich_text": _rich_text(h.known_factors)},
        "Unknown Factors": {"rich_text": _rich_text(h.unknown_factors)},
        "Priced In": {"rich_text": _rich_text(h.priced_in)},
        "Status": {"select": {"name": plan.status}},
    }
    if inv.time_stop:
        properties["Time Stop"] = {"date": {"start": inv.time_stop}}
    if psy.note:
        properties["Psych Notes"] = {"rich_text": _rich_text(psy.note)}

    page = client.pages.create(parent={"database_id": db_id}, properties=properties)
    return page["id"]


def update_trade_status(page_id: str, updates: dict) -> None:
    """更新交易记录的动态字段。"""
    cfg = load_config()
    client = _get_client(cfg)
    properties = {}
    for key, value in updates.items():
        if key in ("Status", "Direction", "Entry Emotion"):
            properties[key] = {"select": {"name": value}}
        elif key == "Technical Confirmed":
            properties[key] = {"checkbox": value}
        elif key in ("Entry Price", "Position %", "Profit Target", "Risk Reward",
                      "Win Rate", "Price Stop", "Actual Exit",
                      "Actual Return %", "R Multiple", "Deviation %", "Familiarity"):
            properties[key] = {"number": value}
        elif key in ("Thesis", "Logic Stop", "Psych Notes", "Known Factors",
                      "Unknown Factors", "Priced In"):
            properties[key] = {"rich_text": _rich_text(value)}
        elif key == "Time Stop" and value:
            properties[key] = {"date": {"start": value}}
    client.pages.update(page_id=page_id, properties=properties)


def close_trade(page_id: str, exit_price: float, notes: str = "") -> dict:
    """关闭交易，自动计算 R-Multiple 和偏差。"""
    cfg = load_config()
    client = _get_client(cfg)

    # 读取原始数据
    page = client.pages.retrieve(page_id=page_id)
    props = page["properties"]
    entry = props["Entry Price"]["number"]
    stop = props["Price Stop"]["number"]
    direction = props["Direction"]["select"]["name"]

    r_mult = calc_r_multiple(entry, exit_price, stop, direction)
    if direction == "LONG":
        ret_pct = (exit_price - entry) / entry
    else:
        ret_pct = (entry - exit_price) / entry
    deviation = abs(exit_price - props["Profit Target"]["number"]) / props["Profit Target"]["number"] if props["Profit Target"]["number"] else 0

    updates = {
        "Status": "CLOSED",
        "Actual Exit": exit_price,
        "Actual Return %": ret_pct,
        "R Multiple": r_mult,
        "Deviation %": deviation,
    }
    if notes:
        updates["Psych Notes"] = notes
    update_trade_status(page_id, updates)
    return {"r_multiple": r_mult, "return_pct": ret_pct, "deviation": deviation}


def add_psych_note(page_id: str, note: str) -> None:
    """追加心理备注。"""
    cfg = load_config()
    client = _get_client(cfg)
    page = client.pages.retrieve(page_id=page_id)
    existing = ""
    rt = page["properties"].get("Psych Notes", {}).get("rich_text", [])
    if rt:
        existing = rt[0].get("text", {}).get("content", "")
    combined = f"{existing}\n---\n{note}" if existing else note
    update_trade_status(page_id, {"Psych Notes": combined})


def fetch_all_trades(status: str | None = None, date_range: tuple | None = None) -> list[dict]:
    """查询交易记录。返回简化的 dict 列表。"""
    client, db_id = ensure_database()
    filters = []
    if status:
        filters.append({"property": "Status", "select": {"equals": status}})
    if date_range:
        start, end = date_range
        filters.append({"timestamp": "created_time", "created_time": {"on_or_after": start}})
        filters.append({"timestamp": "created_time", "created_time": {"on_or_before": end}})

    query_filter = {"and": filters} if filters else None
    kwargs = {"database_id": db_id}
    if query_filter:
        kwargs["filter"] = query_filter

    results = []
    has_more = True
    start_cursor = None
    while has_more:
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = client.databases.query(**kwargs)
        for page in response["results"]:
            results.append(_parse_page(page))
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    return results


def _parse_page(page: dict) -> dict:
    """将 Notion 页面解析为简化 dict。"""
    p = page["properties"]
    return {
        "page_id": page["id"],
        "ticker": _extract_title(p.get("Ticker", {})),
        "direction": _extract_select(p.get("Direction", {})),
        "entry_price": p.get("Entry Price", {}).get("number"),
        "position_pct": (p.get("Position %", {}).get("number") or 0) * 100,
        "profit_target": p.get("Profit Target", {}).get("number"),
        "risk_reward": p.get("Risk Reward", {}).get("number"),
        "win_rate": p.get("Win Rate", {}).get("number"),
        "price_stop": p.get("Price Stop", {}).get("number"),
        "time_stop": _extract_date(p.get("Time Stop", {})),
        "logic_stop": _extract_rich_text(p.get("Logic Stop", {})),
        "entry_emotion": _extract_select(p.get("Entry Emotion", {})),
        "familiarity": p.get("Familiarity", {}).get("number"),
        "technical_confirmed": p.get("Technical Confirmed", {}).get("checkbox", False),
        "thesis": _extract_rich_text(p.get("Thesis", {})),
        "status": _extract_select(p.get("Status", {})),
        "actual_exit": p.get("Actual Exit", {}).get("number"),
        "actual_return_pct": p.get("Actual Return %", {}).get("number"),
        "r_multiple": p.get("R Multiple", {}).get("number"),
        "deviation_pct": p.get("Deviation %", {}).get("number"),
        "psych_notes": _extract_rich_text(p.get("Psych Notes", {})),
        "created": page.get("created_time", ""),
    }


def _extract_title(prop: dict) -> str:
    items = prop.get("title", [])
    return items[0]["text"]["content"] if items else ""


def _extract_select(prop: dict) -> str:
    sel = prop.get("select")
    return sel["name"] if sel else ""


def _extract_rich_text(prop: dict) -> str:
    items = prop.get("rich_text", [])
    return items[0]["text"]["content"] if items else ""


def _extract_date(prop: dict) -> str:
    d = prop.get("date")
    return d["start"] if d else ""
