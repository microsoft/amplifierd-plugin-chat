def test_get_pins_empty(client):
    resp = client.get("/chat/pins")
    assert resp.status_code == 200
    assert resp.json() == {"pinned": []}


def test_pin_session(client):
    resp = client.post("/chat/pins/session-abc")
    assert resp.status_code == 200
    resp = client.get("/chat/pins")
    assert "session-abc" in resp.json()["pinned"]


def test_unpin_session(client):
    client.post("/chat/pins/session-abc")
    resp = client.delete("/chat/pins/session-abc")
    assert resp.status_code == 200
    resp = client.get("/chat/pins")
    assert "session-abc" not in resp.json()["pinned"]


def test_serve_spa(client):
    resp = client.get("/chat/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_serve_vendor_js(client):
    resp = client.get("/chat/vendor.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
