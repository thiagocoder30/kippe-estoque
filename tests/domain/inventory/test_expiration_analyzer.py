from src.domain.services.expiration_analyzer import ExpirationAnalyzer


def test_expiration_analyzer_returns_normal_for_safe_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date="2035-12-31"
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "NORMAL"
    assert data["days_remaining"] > 0


def test_expiration_analyzer_returns_expired_for_past_date():

    result = ExpirationAnalyzer.analyze(
        expiration_date="2020-01-01"
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "VENCIDO"
    assert data["days_remaining"] < 0


def test_expiration_analyzer_returns_critical_for_near_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date="2026-08-18"
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "CRITICO"
    assert data["days_remaining"] <= 7


def test_expiration_analyzer_returns_critical_for_near_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date="2026-08-18"
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "CRITICO"
    assert data["days_remaining"] <= 7


def test_expiration_analyzer_returns_attention_for_medium_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date="2026-09-01"
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "ATENCAO"
    assert 8 <= data["days_remaining"] <= 30
