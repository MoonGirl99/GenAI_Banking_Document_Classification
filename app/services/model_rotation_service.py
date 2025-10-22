"""
Model rotation service for handling Mistral AI rate limits
Automatically switches to fallback models when rate limits are encountered
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ModelRotationService:
    """
    Manages automatic model rotation when rate limits are hit.
    Tracks which models have been rate limited and their cooldown periods.
    """

    def __init__(self, fallback_models: List[str]):
        self.fallback_models = fallback_models
        self.rate_limited_models = {}  # model_name -> timestamp when rate limited
        self.cooldown_period = timedelta(minutes=5)  # Reset after 5 minutes
        self.usage_count = defaultdict(int)  # Track usage per model

    def get_next_available_model(self, current_model: Optional[str] = None) -> str:
        """
        Get the next available model, skipping rate-limited ones.

        Args:
            current_model: The model that was just tried (to skip it)

        Returns:
            Next available model name
        """
        now = datetime.now()

        # Clean up expired rate limits
        self._cleanup_expired_limits(now)

        # Filter out rate-limited models and current model
        available_models = [
            model for model in self.fallback_models
            if model != current_model and not self._is_rate_limited(model, now)
        ]

        if not available_models:
            logger.warning("All models are rate limited! Resetting limits...")
            self.rate_limited_models.clear()
            available_models = self.fallback_models

        # Return the least used available model
        next_model = min(available_models, key=lambda m: self.usage_count[m])
        logger.info(f"Selected model: {next_model} (used {self.usage_count[next_model]} times)")

        return next_model

    def mark_rate_limited(self, model: str):
        """Mark a model as rate limited"""
        self.rate_limited_models[model] = datetime.now()
        logger.warning(f"Model {model} marked as rate limited at {datetime.now()}")

    def mark_success(self, model: str):
        """Mark successful use of a model"""
        self.usage_count[model] += 1
        # Remove from rate limited if it was there
        if model in self.rate_limited_models:
            del self.rate_limited_models[model]
            logger.info(f"Model {model} recovered from rate limit")

    def _is_rate_limited(self, model: str, now: datetime) -> bool:
        """Check if a model is currently rate limited"""
        if model not in self.rate_limited_models:
            return False

        limited_at = self.rate_limited_models[model]
        return (now - limited_at) < self.cooldown_period

    def _cleanup_expired_limits(self, now: datetime):
        """Remove expired rate limits"""
        expired = [
            model for model, limited_at in self.rate_limited_models.items()
            if (now - limited_at) >= self.cooldown_period
        ]
        for model in expired:
            del self.rate_limited_models[model]
            logger.info(f"Rate limit expired for model: {model}")

    def get_status(self) -> dict:
        """Get current status of all models"""
        now = datetime.now()
        self._cleanup_expired_limits(now)

        status = {
            "available_models": [
                m for m in self.fallback_models
                if not self._is_rate_limited(m, now)
            ],
            "rate_limited_models": list(self.rate_limited_models.keys()),
            "usage_stats": dict(self.usage_count),
            "total_models": len(self.fallback_models)
        }
        return status

    def reset(self):
        """Reset all tracking (useful for testing or manual intervention)"""
        self.rate_limited_models.clear()
        self.usage_count.clear()
        logger.info("Model rotation service reset")

