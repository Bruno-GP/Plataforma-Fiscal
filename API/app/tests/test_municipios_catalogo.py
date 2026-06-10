from app.services.Municipios.municipios_catalog_service import MunicipiosCatalogService


def test_listar_ufs_do_catalogo(client, monkeypatch):
    monkeypatch.setattr(
        MunicipiosCatalogService,
        "listar_ufs",
        lambda busca=None: [
            {"uf": "SP", "label": "SP", "quantidade_municipios": 645},
            {"uf": "RJ", "label": "RJ", "quantidade_municipios": 92},
        ],
    )

    response = client.get("/api/municipios/ufs")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["uf"] == "SP"
    assert payload[1]["uf"] == "RJ"


def test_listar_cidades_exige_uf_valida(client, monkeypatch):
    monkeypatch.setattr(
        MunicipiosCatalogService,
        "listar_municipios_por_uf",
        lambda uf, busca=None, limite=None: (
            [{"municipio_id": "3550308", "codigo_ibge": "3550308", "nome": "Sao Paulo", "uf": "SP"}]
            if uf == "SP"
            else []
        ),
    )

    response = client.get("/api/municipios/cidades?uf=SP&busca=sao")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["codigo_ibge"] == "3550308"


def test_listar_cidades_sem_uf_retorna_lista_vazia(client):
    response = client.get("/api/municipios/cidades")

    assert response.status_code == 200
    assert response.json() == []
