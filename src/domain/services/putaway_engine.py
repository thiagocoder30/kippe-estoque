from src.domain.result import Result


class PutawayEngine:

    @staticmethod
    def execute_putaway(
        product,
        batch_code: str,
        location_id: str
    ) -> Result[None, str]:

        if not batch_code:
            return Result.fail(
                "Código do lote obrigatório."
            )

        if not location_id:
            return Result.fail(
                "Localização obrigatória."
            )

        batch = product.batches.get(batch_code)

        if not batch:
            return Result.fail(
                f"Lote não encontrado: {batch_code}"
            )

        batch.location_id = location_id

        return Result.ok(None)
