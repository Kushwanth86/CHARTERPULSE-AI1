import pytest

from services.api.app.intelligence.model_evaluation import ModelEvaluationEngine


def test_evaluate_calculates_accuracy_metrics_and_coverage():
    result = ModelEvaluationEngine.evaluate(
        actual=110,
        p10=90,
        p50=100,
        p90=120,
    )

    assert result["signed_error"] == 10
    assert result["absolute_error"] == 10
    assert result["squared_error"] == 100
    assert result["smape"] == pytest.approx(9.5238095238)
    assert result["interval_covered"] is True


def test_evaluate_marks_actual_outside_interval():
    result = ModelEvaluationEngine.evaluate(
        actual=140,
        p10=90,
        p50=100,
        p90=120,
    )

    assert result["interval_covered"] is False


def test_evaluate_rejects_non_positive_actual():
    with pytest.raises(ValueError, match="greater than zero"):
        ModelEvaluationEngine.evaluate(
            actual=0,
            p10=90,
            p50=100,
            p90=120,
        )


def test_evaluate_rejects_invalid_prediction_interval():
    with pytest.raises(ValueError, match="invalid"):
        ModelEvaluationEngine.evaluate(
            actual=110,
            p10=120,
            p50=100,
            p90=115,
        )


def test_summary_calculates_aggregate_metrics():
    evaluations = [
        {"absolute_error": 10, "squared_error": 100, "smape": 10, "interval_covered": True},
        {"absolute_error": 20, "squared_error": 400, "smape": 20, "interval_covered": False},
    ]

    result = ModelEvaluationEngine.summarize(evaluations)

    assert result["sample_count"] == 2
    assert result["mae"] == 15
    assert result["rmse"] == pytest.approx((250) ** 0.5)
    assert result["smape"] == 15
    assert result["interval_coverage"] == 0.5


def test_summary_requires_observations():
    with pytest.raises(ValueError, match="No forecast evaluations"):
        ModelEvaluationEngine.summarize([])
