import pytest
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import ReceiveGoodsCommand
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
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
def api_router():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Injeção do Bounded Context do Catálogo
    
    query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_api_get_sku_not_found(api_router):
    status, response = api_router.get_sku("999")
    assert status == 404
    assert "não possui histórico" in response["error"]

def test_api_post_receive_and_get_sku_success(api_router):
    # Payload simulando o corpo de uma requisição HTTP POST inbound
    payload = {
        "sku": "789609890001",
        "quantity": 50,
        "supplier": "Distribuidora XPTO",
        "batch_code": "LOTE-API-01",
        "operator": "API_SYS"
    }
    
    status_post, response_post = api_router.post_receive_goods(payload)
    assert status_post == 201
    assert "sucesso" in response_post["message"]
    
    # Validação do CQRS read-side sincronizado com o write-side
    status_get, response_get = api_router.get_sku("789609890001")
    assert status_get == 200
    assert response_get["sku"] == "789609890001"
    assert response_get["balances"]["total"] == 50
    assert response_get["operational_metrics"]["trust_score"] == 100

def test_api_post_receive_validation_error(api_router):
    # Payload corrompido com ausência de campo obrigatório
    payload = {"sku": "789609890001", "quantity": 10}
    status, response = api_router.post_receive_goods(payload)
    
    assert status == 400
    assert "Campo obrigatório ausente" in response["error"]
