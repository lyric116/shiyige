import json

from backend.app.core.database import reset_database_state
from backend.scripts.export_baseline_recommendation_metrics import export_baseline_metrics


def test_export_baseline_recommendation_metrics_creates_repeatable_report(
    monkeypatch,
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'baseline.db'}"
    output_path = tmp_path / "recommendation_baseline_metrics.json"

    monkeypatch.setenv("DATABASE_URL", database_url)
    reset_database_state()

    try:
        payload = export_baseline_metrics(output_path=output_path)
    finally:
        reset_database_state()

    assert output_path.exists()
    saved_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved_payload["provider"]["model_name"]
    assert len(saved_payload["search_cases"]) == 4
    assert len(saved_payload["recommendation_cases"]) == 2
    assert payload == saved_payload

    for case in saved_payload["search_cases"] + saved_payload["recommendation_cases"]:
        assert "query" in case
        assert "user_id" in case
        assert "returned_product_ids" in case
        assert "score" in case
        assert "reason" in case
        assert "latency_ms" in case
        assert case["returned_product_ids"]
        assert case["score"] is not None
        assert case["reason"]
        assert case["latency_ms"] >= 0
        assert case["items"]
