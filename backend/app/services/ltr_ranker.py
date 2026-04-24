from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.services.ranking_features import RecommendationRankingFeatures


@dataclass(slots=True)
class JsonWeightLTRRanker:
    model_version: str
    weights: dict[str, float]
    intercept: float = 0.0

    def score(self, features: RecommendationRankingFeatures) -> float:
        normalized = features.to_normalized_dict()
        score = float(self.intercept)
        for feature_name, weight in self.weights.items():
            score += normalized.get(feature_name, 0.0) * float(weight)
        return score


def load_ltr_ranker(
    settings: AppSettings | None = None,
) -> JsonWeightLTRRanker | None:
    app_settings = settings or get_app_settings()
    model_path = app_settings.recommendation_ltr_model_path
    if not model_path:
        return None

    path = Path(model_path)
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    weights = {
        str(key): float(value)
        for key, value in dict(payload.get("weights", {})).items()
    }
    if not weights:
        return None

    return JsonWeightLTRRanker(
        model_version=str(payload.get("model_version", "ltr-json-v1")),
        weights=weights,
        intercept=float(payload.get("intercept", 0.0)),
    )
