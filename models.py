"""ReflexiveTrader Pro — 数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradeHypothesis:
    ticker: str
    direction: str  # LONG / SHORT / REDUCE_LONG / REDUCE_SHORT
    thesis: str
    familiarity_score: int  # 1-10
    known_factors: str
    unknown_factors: str
    priced_in: str
    technical_confirmed: bool  # 是否有技术面确认


@dataclass
class InvalidationPlan:
    price_stop: float
    time_stop: str  # ISO date string
    logic_stop: str
    profit_target_1: float
    profit_target_2: float
    action_at_target: str  # TAKE_PROFIT / PYRAMID / HOLD


EXTREME_EMOTIONS = {"fearful", "fomo", "fatigued"}
VALID_EMOTIONS = {"confident", "fearful", "fomo", "fatigued", "calm", "exploratory"}


@dataclass
class PsychologyCheck:
    emotion: str  # confident/fearful/fomo/fatigued/calm/exploratory
    is_extreme: bool
    note: str


@dataclass
class PositionPlan:
    win_rate: float
    risk_reward: float
    position_pct: float
    entry_price: float


@dataclass
class TradePlan:
    hypothesis: TradeHypothesis
    invalidation: InvalidationPlan
    psychology: PsychologyCheck
    position: PositionPlan
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "PLANNED"  # PLANNED / ACTIVE / CLOSED
    notion_page_id: str = ""
