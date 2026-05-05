import requests


class FakeChatResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400

    def json(self):
        return self._payload


def test_chat_web_page_renderiza_para_usuario_autenticado(client):
    response = client.get("/chat-web")
    assert response.status_code == 200
    assert "Chat Web" in response.text


def test_chat_web_endpoint_retorna_resposta_normalizada(portal_module, client, monkeypatch):
    def fake_get(url, *args, **kwargs):
        assert url == portal_module.API_LLM_CHAT_URL
        assert kwargs["params"]["string"] == "Como esta o clima?"
        return FakeChatResponse({"response": "Tudo certo!"})

    monkeypatch.setattr(portal_module.requests, "get", fake_get)

    response = client.post("/api/chat/web", json={"message": "Como esta o clima?"})
    assert response.status_code == 200
    assert response.json() == {"reply": "Tudo certo!"}


def test_chat_web_endpoint_bloqueia_mensagem_vazia(client):
    response = client.post("/api/chat/web", json={"message": "   "})
    assert response.status_code == 400
    assert "obrigatoria" in response.json()["detail"]


def test_chat_web_endpoint_trata_falha_upstream_com_erro_amigavel(portal_module, client, monkeypatch):
    def fake_get(url, *args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(portal_module.requests, "get", fake_get)

    response = client.post("/api/chat/web", json={"message": "pergunta valida"})
    assert response.status_code == 502
    assert "Nao foi possivel obter resposta do chat no momento." in response.json()["detail"]


def test_usuario_nao_autenticado_nao_acessa_chat_web(anonymous_client):
    page = anonymous_client.get("/chat-web", follow_redirects=False)
    assert page.status_code == 303
    assert page.headers["location"] == "/login"

    endpoint = anonymous_client.post("/api/chat/web", json={"message": "ola"})
    assert endpoint.status_code == 401
