"""Testes das regras de negócio: filtro [FREE] e extração do link da loja."""

from steam_free_games_monitor.services.deals import extract_store_url, is_free_title


class TestIsFreeTitle:
    def test_tag_padrao_no_inicio(self):
        assert is_free_title("[FREE] Fireside Feelings")

    def test_case_insensitive(self):
        assert is_free_title("[free] jump king")
        assert is_free_title("[Free] Gato Roboto")
        assert is_free_title("[FrEe] Dead Cells")

    def test_tag_no_meio_do_titulo(self):
        assert is_free_title("Oferta [FREE] do dia")

    def test_sem_tag_retorna_false(self):
        assert not is_free_title("Patch notes do grupo")
        assert not is_free_title("FREE")

    def test_titulo_vazio(self):
        assert not is_free_title("")
        assert not is_free_title(None)


class TestExtractStoreUrl:
    def test_link_app_na_descricao_html(self):
        html = (
            '<a class="bb_link" href="https://store.steampowered.com/app/'
            '2990600/Fireside_Feelings/?curator_clanid=6250352" target="_blank">'
            'https://store.steampowered.com/app/2990600/Fireside_Feelings/'
            '?curator_clanid=6250352</a>'
        )
        assert (
            extract_store_url(html)
            == "https://store.steampowered.com/app/2990600/Fireside_Feelings/?curator_clanid=6250352"
        )

    def test_sub_e_bundle(self):
        assert (
            extract_store_url('<a href="https://store.steampowered.com/sub/12345/x">')
            == "https://store.steampowered.com/sub/12345/x"
        )
        assert extract_store_url(
            '<a href="https://store.steampowered.com/bundle/999/">'
        ) == "https://store.steampowered.com/bundle/999/"

    def test_sem_link_retorna_none(self):
        assert extract_store_url("Apenas texto de um anúncio comum.") is None
        assert extract_store_url(
            '<a href="https://steamcommunity.com/groups/jogosbra">grupo</a>'
        ) is None

    def test_html_vazio(self):
        assert extract_store_url("") is None
        assert extract_store_url(None) is None