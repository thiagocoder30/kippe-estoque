import pytest
import os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def container():
    cfg = Config.for_testing()
    c = Container(cfg)
    # Garante banco limpo para o escopo de teste de segurança
    c.operator_repository._init_db()
    with c.operator_repository._get_connection() as conn:
        conn.execute('DELETE FROM operators')
        conn.commit()
    
    yield c
    
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)
    if os.path.exists(cfg.LOG_PATH): os.remove(cfg.LOG_PATH)

def test_operator_pin_is_hashed_and_verified(container):
    auth_uc = container.auth_use_case
    
    # 1. Registro
    res_reg = auth_uc.register("1045", "João Silva", "1234", "OPERADOR")
    assert res_reg.is_success is True
    
    # Validação estrutural de que o banco não salvou '1234'
    operator_raw = container.operator_repository.get_by_id("1045")
    assert operator_raw.pin_hash != "1234"
    assert len(operator_raw.pin_hash) > 20 # Hash do werkzeug é grande
    
    # 2. Autenticação Correta
    res_auth = auth_uc.authenticate("1045", "1234")
    assert res_auth.is_success is True
    assert res_auth.value.name == "João Silva"
    
    # 3. Falha de Autenticação
    res_fail = auth_uc.authenticate("1045", "0000")
    assert res_fail.is_success is False
    assert "Credenciais inválidas" in res_fail.error

def test_operator_creation_validation(container):
    auth_uc = container.auth_use_case
    
    # PIN curto
    res = auth_uc.register("999", "Admin", "12")
    assert res.is_success is False
    
    # Role inválida
    res2 = auth_uc.register("888", "Hacker", "1234", "SUPERUSER")
    assert res2.is_success is False
