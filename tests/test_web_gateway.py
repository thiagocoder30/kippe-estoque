from app import app


def test_health_endpoint():
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["system"] == "KIPPE WMS"
    assert response.json["gateway"] == "flask"


def test_pwa_is_served_by_flask():
    app.config["TESTING"] = True

    with app.test_client() as client:
        root = client.get("/")
        api_js = client.get("/web/js/api.js")
        css = client.get("/web/css/app.css")

    assert root.status_code == 200
    assert api_js.status_code == 200
    assert css.status_code == 200
