from typing import Any, Dict


def purchase_order_v1_0_to_v1_1(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Migra um payload legado de Purchase Order do schema 1.0
    para o schema 1.1 sem modificar o objeto original.
    """
    migrated = dict(data)

    migrated["schema_version"] = "1.1"
    migrated.setdefault(
        "tags",
        ["migrated_from_v1.0"],
    )

    return migrated
