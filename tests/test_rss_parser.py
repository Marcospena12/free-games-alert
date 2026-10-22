"""Testes da interpretação de feeds RSS com feedparser."""

from datetime import datetime, timezone

import pytest

from steam_free_games_monitor.services.rss_parser import RssParseError, parse_feed


def test_parse_feed_valido(sample_feed_bytes):
    items = parse_feed(sample_feed_bytes)
    assert len(items) == 3


def test_extrai_titulo_guid_link_data_autor(sample_items):
    first = sample_items[0]
    assert first.title == "[FREE] Fireside Feelings"
    assert first.guid == "https://steamcommunity.com/groups/jogosbra/announcements/detail/680763661892979390"
    assert first.link == "https://steamcommunity.com/groups/jogosbra/announcements/detail/680763661892979390"
    assert first.author == "DKA"
    assert first.published_at is not None
    expected = datetime(2026, 10, 9, 17, 6, 52, tzinfo=timezone.utc)
    assert first.published_at.replace(tzinfo=timezone.utc).isoformat().startswith(
        "2026-10-09T17:06:52"
    )


def test_descricao_decodificada_contem_link_da_loja(sample_items):
    description = sample_items[0].description
    assert description is not None
    assert "href=" in description
    assert "store.steampowered.com/app/2990600" in description
    assert "&amp;" not in description.lower() or "&quot;" not in description


def test_descricao_ausente_nao_inventa_informacao():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>t</title>
      <item><title>[FREE] Sem descricao</title><guid>x-1</guid></item>
    </channel></rss>"""
    items = parse_feed(xml)
    assert len(items) == 1
    assert items[0].description is None
    assert items[0].author is None
    assert items[0].published_at is None


def test_xml_malformado_lanca_erro():
    with pytest.raises(RssParseError):
        parse_feed(b"<rss><channel><item><title>sem fechar</title>")


def test_conteudo_nao_rss_lanca_erro():
    with pytest.raises(RssParseError):
        parse_feed(b"<html><body>isto nao eh um feed</body></html>")


def test_feed_vazio_valido_retorna_lista_vazia():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>t</title></channel></rss>"""
    assert parse_feed(xml) == []