"""
NF-001J.6 — Deterministic Receiving Identity Contract.

Pure application contract used to identify one fiscal receiving operation
before any stock mutation occurs.

Identity answers:
    "Which fiscal line is this receiving operation?"

Fingerprint answers:
    "What exact receiving payload belongs to that identity?"

This module deliberately does NOT:
- access SQLite;
- access repositories;
- persist idempotency state;
- execute ReceivingUseCase;
- mutate stock;
- create batches;
- execute putaway;
- implement HTTP retry behavior.

Persistence and atomic execution belong to later certified slices.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Optional

from src.application.procurement.receiving_adapter import (
    ReceivingCommand,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffLine,
    StockistHandoffResult,
    StockistHandoffStatus,
)


class ReceivingReplayStatus(str, Enum):
    NEW = "NEW"
    REPLAY = "REPLAY"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class ReceivingIdentity:
    origin_document: str
    supplier_id: str
    invoice_number: str
    line_number: int

    @property
    def canonical_key(self) -> str:
        return "|".join(
            (
                self.origin_document,
                self.supplier_id,
                self.invoice_number,
                str(self.line_number),
            )
        )


@dataclass(frozen=True)
class ReceivingIdentityEnvelope:
    identity: ReceivingIdentity
    fingerprint: str
    command: ReceivingCommand

    @property
    def idempotency_key(self) -> str:
        return self.identity.canonical_key


@dataclass(frozen=True)
class ReceivingReplayDecision:
    status: ReceivingReplayStatus
    identity: ReceivingIdentity
    current_fingerprint: str
    previous_fingerprint: Optional[str]

    @property
    def may_execute(self) -> bool:
        return self.status == ReceivingReplayStatus.NEW

    @property
    def is_safe_replay(self) -> bool:
        return self.status == ReceivingReplayStatus.REPLAY

    @property
    def is_conflict(self) -> bool:
        return self.status == ReceivingReplayStatus.CONFLICT


class ReceivingIdentityService:
    """
    Builds deterministic receiving identity and payload fingerprint.
    """

    @classmethod
    def build(
        cls,
        handoff: StockistHandoffResult,
        *,
        line_number: int,
        command: ReceivingCommand,
    ) -> ReceivingIdentityEnvelope:
        if not isinstance(
            handoff,
            StockistHandoffResult,
        ):
            raise TypeError(
                "Receiving identity requires "
                "StockistHandoffResult."
            )

        if not isinstance(
            command,
            ReceivingCommand,
        ):
            raise TypeError(
                "Receiving identity requires ReceivingCommand."
            )

        line = handoff.get_line(line_number)

        cls._validate_line_and_command(
            handoff=handoff,
            line=line,
            command=command,
        )

        identity = ReceivingIdentity(
            origin_document=cls._required_text(
                command.origin_document,
                "origin_document",
            ),
            supplier_id=cls._required_text(
                handoff.supplier_id,
                "supplier_id",
            ),
            invoice_number=cls._required_text(
                handoff.invoice_number,
                "invoice_number",
            ),
            line_number=cls._positive_line_number(
                line.line_number,
            ),
        )

        fingerprint = cls._fingerprint(
            identity=identity,
            line=line,
            command=command,
        )

        return ReceivingIdentityEnvelope(
            identity=identity,
            fingerprint=fingerprint,
            command=command,
        )

    @classmethod
    def compare(
        cls,
        envelope: ReceivingIdentityEnvelope,
        *,
        previous_fingerprint: Optional[str],
    ) -> ReceivingReplayDecision:
        if not isinstance(
            envelope,
            ReceivingIdentityEnvelope,
        ):
            raise TypeError(
                "Receiving replay comparison requires "
                "ReceivingIdentityEnvelope."
            )

        previous = cls._optional_text(
            previous_fingerprint,
        )

        if previous is None:
            status = ReceivingReplayStatus.NEW

        elif previous == envelope.fingerprint:
            status = ReceivingReplayStatus.REPLAY

        else:
            status = ReceivingReplayStatus.CONFLICT

        return ReceivingReplayDecision(
            status=status,
            identity=envelope.identity,
            current_fingerprint=envelope.fingerprint,
            previous_fingerprint=previous,
        )

    @classmethod
    def _validate_line_and_command(
        cls,
        *,
        handoff: StockistHandoffResult,
        line: StockistHandoffLine,
        command: ReceivingCommand,
    ) -> None:
        if (
            line.status
            != StockistHandoffStatus.READY_FOR_RECEIVING
        ):
            raise ValueError(
                "Receiving identity requires "
                "READY_FOR_RECEIVING line."
            )

        expected = {
            "identifier": cls._required_text(
                line.product_id,
                "product_id",
            ),
            "quantity": line.quantity_to_receive,
            "batch_code": cls._required_text(
                line.batch_code,
                "batch_code",
            ),
            "expiration_date": cls._required_text(
                line.expiration_date,
                "expiration_date",
            ),
            "supplier": cls._required_text(
                handoff.supplier_id,
                "supplier_id",
            ),
            "invoice_id": cls._required_text(
                handoff.invoice_number,
                "invoice_number",
            ),
            "operator_id": cls._required_text(
                line.completed_by,
                "completed_by",
            ),
        }

        actual = {
            "identifier": command.identifier,
            "quantity": command.quantity,
            "batch_code": command.batch_code,
            "expiration_date": command.expiration_date,
            "supplier": command.supplier,
            "invoice_id": command.invoice_id,
            "operator_id": command.operator_id,
        }

        for field_name, expected_value in expected.items():
            if actual[field_name] != expected_value:
                raise ValueError(
                    "Receiving command diverges from "
                    f"certified handoff field: {field_name}."
                )

    @staticmethod
    def _fingerprint(
        *,
        identity: ReceivingIdentity,
        line: StockistHandoffLine,
        command: ReceivingCommand,
    ) -> str:
        payload = {
            "identity": {
                "origin_document": identity.origin_document,
                "supplier_id": identity.supplier_id,
                "invoice_number": identity.invoice_number,
                "line_number": identity.line_number,
            },
            "receiving": {
                "identifier": command.identifier,
                "quantity": command.quantity,
                "batch_code": command.batch_code,
                "expiration_date": command.expiration_date,
                "supplier": command.supplier,
                "manufacturing_date": command.manufacturing_date,
                "invoice_id": command.invoice_id,
                "origin_document": command.origin_document,
                "operator_id": command.operator_id,
            },
            "conference_evidence": {
                "fiscal_quantity": line.fiscal_quantity,
                "quantity_to_receive": line.quantity_to_receive,
                "divergence": line.divergence,
                "counted_by": line.counted_by,
            },
        }

        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _required_text(
        value: Optional[str],
        field_name: str,
    ) -> str:
        normalized = str(
            value or ""
        ).strip()

        if not normalized:
            raise ValueError(
                f"{field_name} is required "
                "for receiving identity."
            )

        return normalized

    @staticmethod
    def _optional_text(
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None

    @staticmethod
    def _positive_line_number(
        value: int,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(
                "line_number must be a positive integer."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                "line_number must be a positive integer."
            ) from None

        if normalized != value or normalized <= 0:
            raise ValueError(
                "line_number must be a positive integer."
            )

        return normalized
