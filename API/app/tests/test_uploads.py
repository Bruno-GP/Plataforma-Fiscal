from types import SimpleNamespace


def test_upload_xml_valido(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )
    monkeypatch.setattr(
        "app.api.nfe.routes.XMLImportacaoService.importar_arquivos",
        lambda self, arquivos, cnpj_empresa_origem: [
            SimpleNamespace(
                arquivo=arquivos[0][0],
                cnpj_emitente=cnpj_empresa_origem,
                status="importado",
                mensagem="ok",
            )
        ],
    )

    with (fixtures_dir / "nfe_valida.xml").open("rb") as arquivo:
        response = client.post(
            "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
            files=[("arquivos", ("nfe_valida.xml", arquivo, "application/xml"))],
        )

    assert response.status_code == 200
    assert response.json()["importados"] == 1


def test_upload_xml_invalido(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )

    with (fixtures_dir / "nfe_invalida.xml").open("rb") as arquivo:
        response = client.post(
            "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
            files=[("arquivos", ("nfe_invalida.xml", arquivo, "application/xml"))],
        )

    assert response.status_code == 400


def test_upload_xml_limite(client, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_XML_BYTES", "1024")
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )

    response = client.post(
        "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
        files=[("arquivos", ("grande.xml", b"<xml>" + b"a" * 2048 + b"</xml>", "application/xml"))],
    )

    assert response.status_code == 400
    assert "excede o limite" in response.json()["detail"]


def test_upload_sped_valido(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )
    monkeypatch.setattr(
        "app.api.sped.routes.SpedImportacaoService.importar_arquivos",
        lambda self, arquivos, cnpj_empresa_origem: [
            SimpleNamespace(
                arquivo=arquivos[0][0],
                cnpj_emitente=cnpj_empresa_origem,
                status="importado",
                mensagem="ok",
            )
        ],
    )

    with (fixtures_dir / "sped_valido.txt").open("rb") as arquivo:
        response = client.post(
            "/api/sped/importar?cnpj_empresa_origem=12345678000190",
            files=[("arquivos", ("sped_valido.txt", arquivo, "text/plain"))],
        )

    assert response.status_code == 200
    assert response.json()["importados"] == 1
