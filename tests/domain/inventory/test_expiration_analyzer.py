from datetime import datetime, timedelta

from src.domain.services.expiration_analyzer import ExpirationAnalyzer


def _date_from_today(days: int) -> str:
    return (
        datetime.now().date() + timedelta(days=days)
    ).isoformat()


def test_expiration_analyzer_returns_normal_for_safe_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date=_date_from_today(60)
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "NORMAL"
    assert data["days_remaining"] == 60


def test_expiration_analyzer_returns_expired_for_past_date():

    result = ExpirationAnalyzer.analyze(
        expiration_date=_date_from_today(-1)
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "VENCIDO"
    assert data["days_remaining"] == -1


def test_expiration_analyzer_returns_critical_for_near_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date=_date_from_today(5)
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "CRITICO"
    assert data["days_remaining"] == 5


def test_expiration_analyzer_returns_attention_for_medium_expiration():

    result = ExpirationAnalyzer.analyze(
        expiration_date=_date_from_today(20)
    )

    assert result.is_success

    data = result.value

    assert data["status"] == "ATENCAO"
    assert data["days_remaining"] == 20


def test_expiration_analyzer_rejects_invalid_date_format():

    result = ExpirationAnalyzer.analyze(
        expiration_date="31-12-2035"
    )

    assert not result.is_success
    assert result.error == "Formato de data inválido"
