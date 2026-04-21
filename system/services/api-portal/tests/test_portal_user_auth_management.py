from uuid import uuid4

from psycopg.rows import dict_row


def _create_user_via_api(client, username: str, password: str, credential: str = "usuario", is_active: bool = True):
    return client.post(
        "/api/users",
        json={
            "username": username,
            "password": password,
            "credential": credential,
            "is_active": is_active,
        },
    )


def _fetch_password_hash(portal_module, username: str):
    with portal_module.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT password_hash FROM portal_users WHERE username = %s;", (username,))
            row = cur.fetchone()
    return None if not row else row["password_hash"]


def test_acesso_sem_login_redireciona_para_login(anonymous_client):
    response = anonymous_client.get("/arquivos", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_valido_cria_sessao_e_permite_navegacao(anonymous_client):
    login = anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login.status_code == 200

    protected = anonymous_client.get("/api/files?page=1&page_size=25")
    assert protected.status_code == 200


def test_login_invalido_retorna_erro_amigavel(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "senha-incorreta"},
    )
    assert response.status_code == 401
    assert "invalidos" in response.json()["detail"]


def test_cadastro_usuario_persiste_hash_forte(portal_module, client):
    username = f"user-{uuid4().hex[:8]}"
    password = "senhaSegura123"

    response = _create_user_via_api(client, username=username, password=password)
    assert response.status_code == 201

    payload = response.json()
    assert payload["username"] == username
    assert "password_hash" not in payload

    stored_hash = _fetch_password_hash(portal_module, username)
    assert stored_hash is not None
    assert stored_hash != password
    assert stored_hash.startswith("pbkdf2_sha256$")


def test_edicao_usuario_atualiza_campos_sem_expor_credenciais(portal_module, client):
    username = f"edit-{uuid4().hex[:8]}"
    create = _create_user_via_api(client, username=username, password="senhaInicial123")
    assert create.status_code == 201
    user_id = create.json()["id"]
    old_hash = _fetch_password_hash(portal_module, username)

    new_username = f"editado-{uuid4().hex[:8]}"
    update = client.put(
        f"/api/users/{user_id}",
        json={
            "username": new_username,
            "credential": "usuario",
            "is_active": True,
            "password": "novaSenha123",
        },
    )
    assert update.status_code == 200

    updated_payload = update.json()
    assert updated_payload["username"] == new_username
    assert "password_hash" not in updated_payload

    new_hash = _fetch_password_hash(portal_module, new_username)
    assert new_hash is not None
    assert new_hash != old_hash


def test_inativacao_usuario_impede_novo_login(client, anonymous_client):
    username = f"inactive-{uuid4().hex[:8]}"
    create = _create_user_via_api(client, username=username, password="senhaAtiva123")
    assert create.status_code == 201
    user_id = create.json()["id"]

    deactivate = client.post(f"/api/users/{user_id}/deactivate")
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    login = anonymous_client.post(
        "/api/auth/login",
        json={"username": username, "password": "senhaAtiva123"},
    )
    assert login.status_code == 401


def test_remocao_fisica_usuario_remove_da_lista(client):
    username = f"delete-{uuid4().hex[:8]}"
    create = _create_user_via_api(client, username=username, password="senhaDelete123")
    assert create.status_code == 201
    user_id = create.json()["id"]

    delete_response = client.delete(f"/api/users/{user_id}")
    assert delete_response.status_code == 200

    listing = client.get("/api/users")
    assert listing.status_code == 200
    usernames = [item["username"] for item in listing.json()["items"]]
    assert username not in usernames


def test_nao_admin_bloqueado_no_crud_de_usuarios(client, anonymous_client):
    username = f"useronly-{uuid4().hex[:8]}"
    create = _create_user_via_api(
        client,
        username=username,
        password="senhaUsuario123",
        credential="usuario",
    )
    assert create.status_code == 201

    login = anonymous_client.post(
        "/api/auth/login",
        json={"username": username, "password": "senhaUsuario123"},
    )
    assert login.status_code == 200

    blocked = anonymous_client.get("/api/users")
    assert blocked.status_code == 403


def test_logout_invalida_sessao(client):
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    after_logout = client.get("/api/files?page=1&page_size=25")
    assert after_logout.status_code == 401
