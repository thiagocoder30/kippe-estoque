import os
from pathlib import Path

import pytest


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

TEST_DB = (
    PROJECT_ROOT
    / "data"
    / "test_strict.db"
)

TEST_LOG = (
    PROJECT_ROOT
    / "data"
    / "test_strict.log"
)

TEST_DB_SIDE_FILES = (
    Path(
        str(TEST_DB)
        + "-shm"
    ),
    Path(
        str(TEST_DB)
        + "-wal"
    ),
)


def _apply_test_environment():
    """
    Proteção global da suíte.

    Este módulo é carregado pelo pytest antes da coleta dos
    módulos em tests/, garantindo que qualquer import posterior
    de app.py crie seu Container já em ambiente de teste.
    """

    os.environ[
        "KIPPE_ENV"
    ] = "testing"

    os.environ[
        "KIPPE_DB_PATH"
    ] = str(
        TEST_DB
    )

    os.environ[
        "KIPPE_LOG_PATH"
    ] = str(
        TEST_LOG
    )

    os.environ[
        "KIPPE_SECRET_KEY"
    ] = (
        "test-crypto-key-signature"
    )


def _remove_test_runtime_files():
    for path in (
        TEST_DB,
        *TEST_DB_SIDE_FILES,
        TEST_LOG,
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


# Executado imediatamente ao pytest importar tests/conftest.py,
# antes da coleta/import dos módulos de teste.
_apply_test_environment()
_remove_test_runtime_files()


@pytest.fixture(
    autouse=True
)
def _enforce_test_environment(
    monkeypatch,
):
    """
    Reaplica a proteção antes de cada teste.

    Alguns contratos exercitam Config e alteram os.environ
    propositalmente. O monkeypatch restaura o estado após cada
    teste, evitando que um caso contamine o seguinte.
    """

    monkeypatch.setenv(
        "KIPPE_ENV",
        "testing",
    )

    monkeypatch.setenv(
        "KIPPE_DB_PATH",
        str(TEST_DB),
    )

    monkeypatch.setenv(
        "KIPPE_LOG_PATH",
        str(TEST_LOG),
    )

    monkeypatch.setenv(
        "KIPPE_SECRET_KEY",
        "test-crypto-key-signature",
    )


def pytest_sessionfinish(
    session,
    exitstatus,
):
    """
    Remove apenas artefatos exclusivos da suíte de testes.

    O banco de produção nunca é referenciado por esta rotina.
    """

    _remove_test_runtime_files()
