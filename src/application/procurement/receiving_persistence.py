"""
NF-001J.7 — Receiving Persistence / Atomicity Contract.

Persistence boundary between deterministic receiving identity (J.6)
and future receiving execution.

This slice deliberately does NOT execute ReceivingUseCase and does
NOT mutate Product, Batch, stock quantity or putaway state.
"""

from dataclasses import dataclass
from typing import Optional

from src.application.procurement.receiving_identity import (
    ReceivingIdentityEnvelope,
    ReceivingReplayDecision,
    ReceivingReplayStatus,
)


@dataclass(frozen=True)
class ReceivingPersistenceResult:
    decision: ReceivingReplayDecision
    operation_status: Optional[str]

    @property
    def may_execute(self) -> bool:
        return self.decision.may_execute


class ReceivingPersistenceService:
    """
    Claims deterministic receiving identity through repository authority.
    """

    @classmethod
    def claim(
        cls,
        repository,
        envelope: ReceivingIdentityEnvelope,
    ) -> ReceivingPersistenceResult:
        if not isinstance(
            envelope,
            ReceivingIdentityEnvelope,
        ):
            raise TypeError(
                "Receiving persistence requires "
                "ReceivingIdentityEnvelope."
            )

        claim = repository.claim_receiving_operation(
            idempotency_key=envelope.idempotency_key,
            fingerprint=envelope.fingerprint,
            origin_document=(
                envelope.identity.origin_document
            ),
            supplier_id=envelope.identity.supplier_id,
            invoice_number=(
                envelope.identity.invoice_number
            ),
            line_number=envelope.identity.line_number,
        )

        status = ReceivingReplayStatus(
            claim["status"]
        )

        decision = ReceivingReplayDecision(
            status=status,
            identity=envelope.identity,
            current_fingerprint=(
                claim["current_fingerprint"]
            ),
            previous_fingerprint=(
                claim["previous_fingerprint"]
            ),
        )

        return ReceivingPersistenceResult(
            decision=decision,
            operation_status=claim.get(
                "operation_status"
            ),
        )
