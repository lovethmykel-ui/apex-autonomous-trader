"""
Apex Autonomous Trader — Evolution Engine
==========================================
Layer 6: Improve future generations.

Analyzes performance data to evolve strategy parameters.
Each new generation inherits optimized params from the last.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.db.models import (
    Generation, GenerationStatus, StrategyPerformance,
    EvolutionParams, TradeMemory
)

logger = logging.getLogger("evolution")


class EvolutionEngine:
    """
    The self-improvement system.
    Analyzes trade history and evolves strategy parameters.
    """

    # Default strategy parameters (Generation 1 starting point)
    DEFAULT_PARAMS = {
        "trend_following": {
            "ema_fast": 9,
            "ema_slow": 50,
            "adx_threshold": 25,
            "min_confidence": 60,
            "weight": 1.0,
        },
        "momentum": {
            "rsi_long_threshold": 55,
            "rsi_short_threshold": 45,
            "roc_min": 0.5,
            "min_confidence": 50,
            "weight": 0.8,
        },
        "breakout": {
            "bb_period": 20,
            "bb_std": 2.0,
            "volume_confirm_ratio": 1.5,
            "min_confidence": 65,
            "weight": 0.7,
        },
        "mean_reversion": {
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "min_confidence": 70,
            "weight": 0.6,
        },
        "funding_rate": {
            "extreme_threshold": 0.01,
            "min_confidence": 60,
            "weight": 0.5,
        },
    }

    @classmethod
    def initialize_generation(cls, db: Session, generation: Generation):
        """
        Initialize strategy parameters for a new generation.
        Inherits from the previous generation if one exists.
        """
        # Find previous generation
        prev_gen = db.query(Generation).filter(
            Generation.number == generation.number - 1
        ).first()

        if prev_gen:
            # Inherit and evolve from previous generation
            params = cls._evolve_params(db, prev_gen)
            logger.info(f"G-{generation.number:02d} inheriting evolved params from G-{prev_gen.number:02d}")
        else:
            # First generation — use defaults
            params = cls.DEFAULT_PARAMS.copy()
            logger.info(f"G-{generation.number:02d} starting with default parameters")

        # Save parameters
        for strategy_name, strategy_params in params.items():
            ep = EvolutionParams(
                generation_id=generation.id,
                strategy_name=strategy_name,
                parameters=strategy_params,
                fitness_score=0.0,
            )
            db.add(ep)

        db.commit()

    @classmethod
    def _evolve_params(cls, db: Session, prev_generation: Generation) -> Dict[str, Dict]:
        """
        Evolve parameters based on previous generation's performance.
        Strategies that performed well get stronger weights.
        Strategies that performed poorly get adjusted parameters.
        """
        # Get previous generation's params
        prev_params = {}
        for ep in db.query(EvolutionParams).filter(
            EvolutionParams.generation_id == prev_generation.id
        ).all():
            prev_params[ep.strategy_name] = ep.parameters.copy()

        # Get performance stats
        performances = {}
        for sp in db.query(StrategyPerformance).filter(
            StrategyPerformance.generation_id == prev_generation.id
        ).all():
            performances[sp.strategy_name] = {
                "win_rate": sp.win_rate,
                "total_pnl": sp.total_pnl,
                "total_trades": sp.total_trades,
                "sharpe": sp.sharpe_ratio,
                "fitness": sp.fitness_score,
            }

        # Evolve each strategy
        evolved = {}
        for strategy_name in cls.DEFAULT_PARAMS:
            base = prev_params.get(strategy_name, cls.DEFAULT_PARAMS[strategy_name]).copy()
            perf = performances.get(strategy_name)

            if perf and perf["total_trades"] >= 5:
                # Adjust weight based on performance
                if perf["win_rate"] > 60 and perf["total_pnl"] > 0:
                    # Winning strategy — increase weight
                    base["weight"] = min(2.0, base.get("weight", 1.0) * 1.15)
                    # Slightly lower confidence threshold (trade more)
                    if "min_confidence" in base:
                        base["min_confidence"] = max(40, base["min_confidence"] - 3)
                elif perf["win_rate"] < 40 or perf["total_pnl"] < 0:
                    # Losing strategy — decrease weight
                    base["weight"] = max(0.1, base.get("weight", 1.0) * 0.8)
                    # Raise confidence threshold (trade less)
                    if "min_confidence" in base:
                        base["min_confidence"] = min(90, base["min_confidence"] + 5)

            evolved[strategy_name] = base

        return evolved

    @classmethod
    def update_strategy_performance(
        cls,
        db: Session,
        generation: Generation,
    ):
        """
        Recalculate strategy performance stats from trade memories.
        Called periodically or after each trade.
        """
        strategies = db.query(
            TradeMemory.strategy_used,
            func.count(TradeMemory.id).label("total"),
            func.sum(TradeMemory.pnl).label("total_pnl"),
            func.avg(TradeMemory.pnl).label("avg_pnl"),
            func.max(TradeMemory.pnl).label("best_pnl"),
            func.min(TradeMemory.pnl).label("worst_pnl"),
            func.avg(TradeMemory.duration_seconds).label("avg_duration"),
        ).filter(
            TradeMemory.generation_id == generation.id,
            TradeMemory.closed_at.isnot(None),
            TradeMemory.strategy_used.isnot(None),
        ).group_by(TradeMemory.strategy_used).all()

        for row in strategies:
            name = row.strategy_used
            if not name:
                continue

            # Count wins
            wins = db.query(func.count(TradeMemory.id)).filter(
                TradeMemory.generation_id == generation.id,
                TradeMemory.strategy_used == name,
                TradeMemory.pnl > 0,
                TradeMemory.closed_at.isnot(None),
            ).scalar() or 0

            losses = (row.total or 0) - wins

            # Calculate fitness score
            win_rate = (wins / row.total * 100) if row.total > 0 else 0
            fitness = cls._calculate_fitness(
                win_rate=win_rate,
                total_pnl=row.total_pnl or 0,
                avg_pnl=row.avg_pnl or 0,
                total_trades=row.total or 0,
            )

            # Upsert StrategyPerformance
            sp = db.query(StrategyPerformance).filter(
                StrategyPerformance.generation_id == generation.id,
                StrategyPerformance.strategy_name == name,
            ).first()

            if not sp:
                sp = StrategyPerformance(
                    generation_id=generation.id,
                    strategy_name=name,
                )
                db.add(sp)

            sp.total_trades = row.total or 0
            sp.wins = wins
            sp.losses = losses
            sp.total_pnl = row.total_pnl or 0
            sp.avg_pnl = row.avg_pnl or 0
            sp.best_trade_pnl = row.best_pnl or 0
            sp.worst_trade_pnl = row.worst_pnl or 0
            sp.avg_duration_seconds = int(row.avg_duration or 0)
            sp.fitness_score = fitness

        db.commit()

    @staticmethod
    def _calculate_fitness(
        win_rate: float,
        total_pnl: float,
        avg_pnl: float,
        total_trades: int,
    ) -> float:
        """
        Calculate overall fitness score for a strategy.
        Considers: win rate, profitability, consistency, sample size.
        """
        score = 0

        # Win rate contribution (0-40)
        score += min(40, win_rate * 0.6)

        # Profitability contribution (0-30)
        if total_pnl > 0:
            score += min(30, total_pnl * 0.1)
        else:
            score += max(-15, total_pnl * 0.05)

        # Consistency (avg pnl positive = good)
        if avg_pnl > 0:
            score += 15
        else:
            score -= 5

        # Sample size bonus (more trades = more reliable)
        score += min(15, total_trades * 0.5)

        return max(0, min(100, round(score, 1)))

    @classmethod
    def get_strategy_weights(cls, db: Session, generation_id: int) -> Dict[str, float]:
        """Get current strategy weights for the decision engine."""
        params = db.query(EvolutionParams).filter(
            EvolutionParams.generation_id == generation_id
        ).all()

        weights = {}
        for ep in params:
            weights[ep.strategy_name] = ep.parameters.get("weight", 1.0)

        # Fill in defaults for any missing strategies
        for name, default in cls.DEFAULT_PARAMS.items():
            if name not in weights:
                weights[name] = default.get("weight", 1.0)

        return weights
