from datetime import datetime

from src.domain.result import Result


class ExpirationAnalyzer:

    @staticmethod
    def analyze(expiration_date: str) -> Result[dict, str]:

        try:
            expiration = datetime.strptime(
                expiration_date,
                "%Y-%m-%d"
            )
        except ValueError:
            return Result.fail(
                "Formato de data inválido"
            )

        today = datetime.now()

        days_remaining = (
            expiration.date() - today.date()
        ).days

        if days_remaining < 0:
            status = "VENCIDO"
        elif days_remaining <= 7:
            status = "CRITICO"
        elif days_remaining <= 30:
            status = "ATENCAO"
        else:
            status = "NORMAL"

        return Result.ok({
            "expiration_date": expiration_date,
            "days_remaining": days_remaining,
            "status": status,
        })
