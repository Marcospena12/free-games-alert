"""Testes da configuração de dados e da migração do banco antigo."""

from __future__ import annotations

from free_games_hub import config


def test_data_dir_respeita_novo_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FGH_DATA_DIR", str(tmp_path / "dados"))
    monkeypatch.delenv("SFGM_DATA_DIR", raising=False)

    path = config.data_dir()

    assert path == tmp_path / "dados"
    assert path.is_dir()


def test_data_dir_aceita_override_antigo(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FGH_DATA_DIR", raising=False)
    monkeypatch.setenv("SFGM_DATA_DIR", str(tmp_path / "legado"))

    path = config.data_dir()

    assert path == tmp_path / "legado"
    assert path.is_dir()


def test_migra_banco_da_versao_antiga(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FGH_DATA_DIR", raising=False)
    monkeypatch.delenv("SFGM_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_base_dir", lambda: tmp_path)

    legacy_dir = tmp_path / config._legacy_folder()
    legacy_dir.mkdir()
    legacy_db = legacy_dir / config.LEGACY_DB_FILENAME
    legacy_db.write_bytes(b"conteudo-antigo")

    target = tmp_path / config._app_folder()
    target.mkdir()

    assert config.migrate_legacy_data(target) is True
    assert (target / config.DB_FILENAME).read_bytes() == b"conteudo-antigo"
    assert config.migrate_legacy_data(target) is False


def test_migracao_nao_sobrescreve_banco_existente(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FGH_DATA_DIR", raising=False)
    monkeypatch.delenv("SFGM_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_base_dir", lambda: tmp_path)

    legacy_dir = tmp_path / config._legacy_folder()
    legacy_dir.mkdir()
    (legacy_dir / config.LEGACY_DB_FILENAME).write_bytes(b"antigo")

    target = tmp_path / config._app_folder()
    target.mkdir()
    (target / config.DB_FILENAME).write_bytes(b"atual")

    assert config.migrate_legacy_data(target) is False
    assert (target / config.DB_FILENAME).read_bytes() == b"atual"


def test_database_path_dispara_migracao(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FGH_DATA_DIR", raising=False)
    monkeypatch.delenv("SFGM_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_base_dir", lambda: tmp_path)

    legacy_dir = tmp_path / config._legacy_folder()
    legacy_dir.mkdir()
    (legacy_dir / config.LEGACY_DB_FILENAME).write_bytes(b"antigo")

    path = config.database_path()

    assert path == tmp_path / config._app_folder() / config.DB_FILENAME
    assert path.read_bytes() == b"antigo"


def test_override_desativa_migracao(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FGH_DATA_DIR", raising=False)
    monkeypatch.delenv("SFGM_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_base_dir", lambda: tmp_path)

    legacy_dir = tmp_path / config._legacy_folder()
    legacy_dir.mkdir()
    (legacy_dir / config.LEGACY_DB_FILENAME).write_bytes(b"antigo")

    monkeypatch.setenv("FGH_DATA_DIR", str(tmp_path / "portatil"))
    target = config.data_dir()

    assert config.migrate_legacy_data(target) is False
    assert not (target / config.DB_FILENAME).exists()
