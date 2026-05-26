from types import SimpleNamespace


def _resultado(arquivo, cnpj, status, mensagem="ok"):
    return SimpleNamespace(
        arquivo=arquivo,
        cnpj_emitente=cnpj,
        status=status,
        mensagem=mensagem,
    )


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


def test_upload_xml_rejeita_empresa_sped(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )

    with (fixtures_dir / "nfe_valida.xml").open("rb") as arquivo:
        response = client.post(
            "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
            files=[("arquivos", ("nfe_valida.xml", arquivo, "application/xml"))],
        )

    assert response.status_code == 400
    assert "SPED Fiscal" in response.json()["detail"]


def test_upload_xml_preserva_resumo_parcial_importado_duplicado_e_erro(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )
    monkeypatch.setattr(
        "app.api.nfe.routes.XMLImportacaoService.importar_arquivos",
        lambda self, arquivos, cnpj_empresa_origem: [
            _resultado("nfe_valida.xml", cnpj_empresa_origem, "importado"),
            _resultado("nfe_duplicada.xml", cnpj_empresa_origem, "duplicado", "duplicado"),
            _resultado("nfe_erro.xml", cnpj_empresa_origem, "erro", "erro"),
        ],
    )

    with (fixtures_dir / "nfe_valida.xml").open("rb") as arquivo:
        content = arquivo.read()

    response = client.post(
        "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
        files=[
            ("arquivos", ("nfe_valida.xml", content, "application/xml")),
            ("arquivos", ("nfe_duplicada.xml", content, "application/xml")),
            ("arquivos", ("nfe_erro.xml", content, "application/xml")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_arquivos"] == 3
    assert payload["importados"] == 1
    assert payload["duplicados"] == 1
    assert payload["erros"] == 1
    assert [item["status"] for item in payload["resultados"]] == ["importado", "duplicado", "erro"]


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


def test_upload_xml_rejeita_extensao_nao_xml(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )

    response = client.post(
        "/api/nfe/xml/importar?cnpj_empresa_origem=12345678000190",
        files=[("arquivos", ("nota.txt", b"<xml/>", "text/plain"))],
    )

    assert response.status_code == 400
    assert ".xml" in response.json()["detail"]


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


def test_upload_sped_rejeita_empresa_xml(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )

    with (fixtures_dir / "sped_valido.txt").open("rb") as arquivo:
        response = client.post(
            "/api/sped/importar?cnpj_empresa_origem=12345678000190",
            files=[("arquivos", ("sped_valido.txt", arquivo, "text/plain"))],
        )

    assert response.status_code == 400
    assert "XML" in response.json()["detail"]


def test_upload_sped_preserva_resumo_parcial_importado_duplicado_e_erro(client, fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )
    monkeypatch.setattr(
        "app.api.sped.routes.SpedImportacaoService.importar_arquivos",
        lambda self, arquivos, cnpj_empresa_origem: [
            _resultado("sped_valido.txt", cnpj_empresa_origem, "importado"),
            _resultado("sped_duplicado.txt", cnpj_empresa_origem, "duplicado", "duplicado"),
            _resultado("sped_erro.txt", cnpj_empresa_origem, "erro", "erro"),
        ],
    )

    with (fixtures_dir / "sped_valido.txt").open("rb") as arquivo:
        content = arquivo.read()

    response = client.post(
        "/api/sped/importar?cnpj_empresa_origem=12345678000190",
        files=[
            ("arquivos", ("sped_valido.txt", content, "text/plain")),
            ("arquivos", ("sped_duplicado.txt", content, "text/plain")),
            ("arquivos", ("sped_erro.txt", content, "text/plain")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_arquivos"] == 3
    assert payload["importados"] == 1
    assert payload["duplicados"] == 1
    assert payload["erros"] == 1
    assert [item["status"] for item in payload["resultados"]] == ["importado", "duplicado", "erro"]


def test_upload_sped_rejeita_extensao_nao_txt(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )

    response = client.post(
        "/api/sped/importar?cnpj_empresa_origem=12345678000190",
        files=[("arquivos", ("sped.xml", b"|0000|12345678000190|", "application/xml"))],
    )

    assert response.status_code == 400
    assert ".txt" in response.json()["detail"]


def test_upload_sped_rejeita_txt_vazio(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )

    response = client.post(
        "/api/sped/importar?cnpj_empresa_origem=12345678000190",
        files=[("arquivos", ("sped.txt", b"", "text/plain"))],
    )

    assert response.status_code == 400
    assert "vazio" in response.json()["detail"]


def test_pendencias_xml_e_sped_preservam_shape(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )
    monkeypatch.setattr("app.api.nfe.routes.XMLImportacaoService.contar_xmls_pendentes", lambda self, cnpj: 2)
    monkeypatch.setattr("app.api.sped.routes.SpedImportacaoService.contar_pendentes", lambda self, cnpj: 3)

    xml = client.get("/api/nfe/xml/pendencias?cnpj_emitente=12345678000190")
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )
    sped = client.get("/api/sped/pendencias?cnpj_emitente=12345678000190")

    assert xml.status_code == 200
    assert xml.json() == {
        "status": "ok",
        "cnpj_emitente": "12345678000190",
        "total_pendentes": 2,
        "possui_pendentes": True,
    }
    assert sped.status_code == 200
    assert sped.json() == {
        "status": "ok",
        "cnpj_emitente": "12345678000190",
        "total_pendentes": 3,
        "possui_pendentes": True,
    }


def test_processar_importados_sem_pendencias_retorna_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.nfe.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: False,
    )
    monkeypatch.setattr("app.api.nfe.routes.XMLImportacaoService.contar_xmls_pendentes", lambda self, cnpj: 0)
    monkeypatch.setattr("app.api.sped.routes.SpedImportacaoService.contar_pendentes", lambda self, cnpj: 0)

    xml = client.post("/api/nfe/xml/processar-importados?cnpj_emitente=12345678000190")
    monkeypatch.setattr(
        "app.api.sped.routes.CompanyProfileService.empresa_tem_sped",
        lambda self, cnpj: True,
    )
    sped = client.post("/api/sped/processar-importados?cnpj_emitente=12345678000190")

    assert xml.status_code == 404
    assert "pendente" in xml.json()["detail"]
    assert sped.status_code == 404
    assert "pendente" in sped.json()["detail"]
