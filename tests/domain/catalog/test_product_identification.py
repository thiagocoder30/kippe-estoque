from src.domain.product import Product


def test_product_accepts_ean():

    product = Product(
        id="SKU-001",
        name="Leite Integral 1L",
        ean="7891234567890"
    )

    assert product.ean == "7891234567890"


def test_product_matches_ean():

    product = Product(
        id="SKU-002",
        name="Arroz 5kg",
        ean="7899999999999"
    )

    assert product.matches_identifier("7899999999999")


def test_product_matches_description():

    product = Product(
        id="SKU-003",
        name="Leite Integral 1L",
        ean="7891111111111"
    )

    assert product.matches_identifier("leite")


def test_product_does_not_match_unknown_identifier():

    product = Product(
        id="SKU-004",
        name="Feijão 1kg",
        ean="7892222222222"
    )

    assert not product.matches_identifier("cafe")
