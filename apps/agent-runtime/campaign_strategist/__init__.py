"""Meta Campaign Strategist: creative insight, market research and a rules-checked Meta campaign plan."""
from .agent import CampaignStrategist
from .rules import apply_rules
from .schemas import StrategyOutput

__all__ = ["CampaignStrategist", "apply_rules", "StrategyOutput"]
