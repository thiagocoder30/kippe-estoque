from pathlib import Path


PRODUCTION_DB = (
    Path("data/estoque_producao.db")
    .resolve()
)


def test_pytest_bootstrap_marks_application_environment_as_testing():
    import app as app_module

    assert (
        app_module.container.config.ENV
        == "testing"
    )


def test_pytest_bootstrap_never_points_app_container_to_production_database():
    import app as app_module

    configured = Path(
        app_module.container.config.DB_PATH
    ).resolve()

    assert (
        configured
        != PRODUCTION_DB
    )


def test_pytest_bootstrap_uses_dedicated_test_database():
    import app as app_module

    configured = Path(
        app_module.container.config.DB_PATH
    )

    assert (
        configured.name
        == "test_strict.db"
    )


def test_pytest_bootstrap_uses_test_log():
    import app as app_module

    configured = Path(
        app_module.container.config.LOG_PATH
    )

    assert (
        configured.name
        == "test_strict.log"
    )
