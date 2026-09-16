"""
NF-001E — Explicit Human Product Onboarding Orchestration

RED contract.

Architectural boundary:

SupplierInvoice
    -> preparation
    -> reconciliation
    -> unresolved workflow
    -> PendingCatalogAction
    -> HUMAN DECISION
    -> explicit product onboarding orchestration
    -> existing catalog authority

This contract intentionally requires a new application boundary.

The orchestration MUST NOT:
- automatically consume unresolved actions;
- infer missing catalog master data;
- receive stock;
- mutate stock quantities;
- perform putaway;
- silently transform invoice evidence into a product.

A human operator must explicitly provide/confirm the product master data
before catalog creation is delegated to the existing repository authority.
"""

import inspect

import pytest


def _import_subject():
    from src.application.procurement.product_onboarding_orchestration import (
        HumanProductOnboardingCommand,
        HumanProductOnboardingOrchestrator,
    )

    return (
        HumanProductOnboardingCommand,
        HumanProductOnboardingOrchestrator,
    )


class RepositorySpy:
    def __init__(self):
        self.register_calls = []

    def register_new_product(
        self,
        name,
        ean,
        unit_of_measure="un",
        status="ATIVO",
        category_id=None,
    ):
        self.register_calls.append(
            {
                "name": name,
                "ean": ean,
                "unit_of_measure": unit_of_measure,
                "status": status,
                "category_id": category_id,
            }
        )

        return {
            "id": "PRODUCT-001",
            "name": name,
            "ean": ean,
            "unit_of_measure": unit_of_measure,
            "status": status,
            "category_id": category_id,
        }


class ForbiddenStockAuthority:
    def __getattr__(self, name):
        raise AssertionError(
            f"NF-001E must not access stock authority: {name}"
        )


def _command(
    HumanProductOnboardingCommand,
    **overrides,
):
    payload = {
        "pending_reason": "UNKNOWN_GTIN",
        "invoice_number": "NF-001E-TEST",
        "supplier_id": "SUPPLIER-001",
        "line_number": 1,
        "fiscal_description": "CAFE TESTE 500G",
        "fiscal_gtin": "7891111111111",
        "fiscal_quantity": 10,
        "fiscal_unit": "CX",
        "confirmed_name": "Café Teste 500g",
        "confirmed_ean": "7891111111111",
        "confirmed_unit_of_measure": "un",
        "confirmed_category_id": None,
    }
    payload.update(overrides)

    return HumanProductOnboardingCommand(**payload)


def test_nf001e_contract_types_exist():
    (
        HumanProductOnboardingCommand,
        HumanProductOnboardingOrchestrator,
    ) = _import_subject()

    assert inspect.isclass(HumanProductOnboardingCommand)
    assert inspect.isclass(HumanProductOnboardingOrchestrator)


def test_nf001e_requires_explicit_human_confirmed_master_data():
    (
        HumanProductOnboardingCommand,
        _,
    ) = _import_subject()

    with pytest.raises((TypeError, ValueError)):
        _command(
            HumanProductOnboardingCommand,
            confirmed_name="",
        )

    with pytest.raises((TypeError, ValueError)):
        _command(
            HumanProductOnboardingCommand,
            confirmed_ean="",
        )

    with pytest.raises((TypeError, ValueError)):
        _command(
            HumanProductOnboardingCommand,
            confirmed_unit_of_measure="",
        )


def test_nf001e_preserves_fiscal_evidence_separately_from_confirmed_master_data():
    (
        HumanProductOnboardingCommand,
        _,
    ) = _import_subject()

    command = _command(
        HumanProductOnboardingCommand,
        fiscal_description="CAFE FISCAL CX 10X500G",
        fiscal_gtin="7891111111111",
        fiscal_unit="CX",
        confirmed_name="Café Torrado 500g",
        confirmed_ean="7899999999999",
        confirmed_unit_of_measure="un",
    )

    assert command.fiscal_description == "CAFE FISCAL CX 10X500G"
    assert command.fiscal_gtin == "7891111111111"
    assert command.fiscal_unit == "CX"

    assert command.confirmed_name == "Café Torrado 500g"
    assert command.confirmed_ean == "7899999999999"
    assert command.confirmed_unit_of_measure == "un"


def test_nf001e_delegates_only_catalog_creation_to_existing_authority():
    (
        HumanProductOnboardingCommand,
        HumanProductOnboardingOrchestrator,
    ) = _import_subject()

    repository = RepositorySpy()

    orchestrator = HumanProductOnboardingOrchestrator(
        repository=repository,
    )

    command = _command(
        HumanProductOnboardingCommand,
    )

    result = orchestrator.execute(command)

    assert len(repository.register_calls) == 1

    call = repository.register_calls[0]

    assert call == {
        "name": "Café Teste 500g",
        "ean": "7891111111111",
        "unit_of_measure": "un",
        "status": "ATIVO",
        "category_id": None,
    }

    assert result is not None


def test_nf001e_does_not_accept_quantity_as_catalog_creation_authority():
    (
        _,
        HumanProductOnboardingOrchestrator,
    ) = _import_subject()

    signature = inspect.signature(
        HumanProductOnboardingOrchestrator.__init__
    )

    forbidden_dependencies = {
        "stock",
        "stock_use_case",
        "manage_stock",
        "receiving",
        "receiving_use_case",
        "existing_stock_onboarding",
        "existing_stock_onboarding_use_case",
        "putaway",
    }

    assert forbidden_dependencies.isdisjoint(
        set(signature.parameters)
    )


def test_nf001e_has_no_automatic_unresolved_workflow_dependency():
    (
        _,
        HumanProductOnboardingOrchestrator,
    ) = _import_subject()

    signature = inspect.signature(
        HumanProductOnboardingOrchestrator.__init__
    )

    forbidden_dependencies = {
        "unresolved_workflow",
        "unresolved_product_workflow",
        "reconciliation",
        "invoice",
    }

    assert forbidden_dependencies.isdisjoint(
        set(signature.parameters)
    )


def test_nf001e_fiscal_quantity_is_evidence_not_stock_mutation():
    (
        HumanProductOnboardingCommand,
        HumanProductOnboardingOrchestrator,
    ) = _import_subject()

    repository = RepositorySpy()

    orchestrator = HumanProductOnboardingOrchestrator(
        repository=repository,
    )

    command = _command(
        HumanProductOnboardingCommand,
        fiscal_quantity=999,
    )

    orchestrator.execute(command)

    assert len(repository.register_calls) == 1

    call = repository.register_calls[0]

    assert "quantity" not in call
    assert "stock" not in call
    assert "batch" not in call
    assert "location" not in call


def test_nf001e_command_does_not_hide_stock_execution_fields():
    (
        HumanProductOnboardingCommand,
        _,
    ) = _import_subject()

    signature = inspect.signature(
        HumanProductOnboardingCommand
    )

    forbidden_fields = {
        "batch_code",
        "expiration_date",
        "manufacturing_date",
        "location_id",
        "historical_receipt_date",
        "historical_basis",
    }

    assert forbidden_fields.isdisjoint(
        set(signature.parameters)
    )
