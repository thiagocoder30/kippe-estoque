import pytest
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.application.warehouse.use_cases.transfer_to_store import TransferToStoreHandler
from src.application.warehouse.use_cases.register_adjustment import RegisterAdjustmentHandler
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)
    def get_all(self):
        return list(self.accounts.values())

@pytest.fixture
def e2e_system():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Contém SKU 789609890001
    
    query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
    bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_holy_trinity_operational_flow_e2e(e2e_system):
    """
    Testa o ciclo de vida completo:
    Entrada -> Movimentação -> Divergência -> Verificação de Risco
    Garantindo que a camada REST orquestra o CQRS perfeitamente.
    """
    sku = "789609890001"
    
    # 1. ENTRADA DE MERCADORIA
    status, _ = e2e_system.post_receive_goods({
        "sku": sku, "quantity": 200, "supplier": "Indústria Ypê",
        "batch_code": "L26-MAX", "expiration_date": "2026-12-31",
        "invoice_id": "NF-999", "operator": "Thiago"
    })
    assert status == 201

    # 2. MOVIMENTAÇÃO PARA LOJA
    status, _ = e2e_system.post_transfer_to_store({
        "sku": sku, "quantity": 40, "batch_code": "L26-MAX", "operator": "Repositor A"
    })
    assert status == 201

    # 3. DIVERGÊNCIA OPERACIONAL (Retirada não registada detetada em contagem)
    status, _ = e2e_system.post_register_adjustment({
        "sku": sku, "quantity": -5, "batch_code": "L26-MAX", 
        "divergence_type": "UNREGISTERED_WITHDRAWAL", 
        "reason": "Produto não encontrado na prateleira", "operator": "Auditor B"
    })
    assert status == 201

    # 4. VERIFICAÇÃO FINAL (O Momento da Verdade do Read Model)
    status, view_json = e2e_system.get_sku(sku)
    assert status == 200
    
    balances = view_json["balances"]
    metrics = view_json["operational_metrics"]
    
    # Validação de Matemática de Saldo
    assert balances["total"] == 195  # 200 recebidos - 5 perdidos
    assert balances["store"] == 40   # 40 enviados
    assert balances["depot"] == 155  # 200 recebidos - 40 enviados - 5 perdidos
    
    # Validação de Qualidade / Confiança
    assert metrics["trust_score"] < 100 # Foi penalizado pela divergência
    assert metrics["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] 
    # Com 5 unidades de volume de ajuste, a matemática do domínio reagiu
