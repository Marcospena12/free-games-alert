# Free Games Hub

[![CI](https://github.com/Marcospena12/free-games-alert/actions/workflows/ci.yml/badge.svg)](https://github.com/Marcospena12/free-games-alert/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

Monitor de jogos gratuitos com suporte a feeds RSS da comunidade Steam e integração multi-loja via GamerPower API (Steam, Epic Games Store, GOG, Itch.io, Ubisoft Connect, Battle.net, EA App, Prime Gaming, DRM-Free, Consoles e Mobile). Focado em simplicidade, confiabilidade e portabilidade entre Windows e Linux.

## Objetivo

O Free Games Hub monitora ofertas de jogos 100% gratuitos a partir de múltiplas fontes confiáveis:
1. **Feeds RSS de grupos da comunidade Steam** (detecta publicações com a marca `[FREE]`).
2. **GamerPower API** (fonte global multi-loja que reúne giveaways ativos da Steam, Epic Games Store, GOG, Itch.io, DRM-Free, PlayStation, Xbox, Switch e Mobile).

A aplicação é puramente desktop, não depende de n8n, serviços pagos ou APIs de IA.

## Fontes de Dados e Atribuição

- **GamerPower API:** Este aplicativo utiliza a API pública oficial da [GamerPower.com](https://www.gamerpower.com) para obter dados em tempo real sobre ofertas ativas em múltiplas plataformas.
  * *Atribuição legal:* Conforme os termos de uso da GamerPower, todas as notificações e visualizações associadas a essa fonte creditam os dados com link direto à **GamerPower.com**.
  * *Limitação:* A GamerPower API não categoriza ofertas por gênero/tags; portanto, filtros por gênero não estão incluídos nesta fonte.

## Tecnologias utilizadas

- **Python 3.12+**
- **PySide6** (interface desktop Qt)
- **feedparser** (leitura e análise de feeds RSS/Atom)
- **sqlite3** (persistência local, via módulo padrão, Schema v4)
- **desktop-notifier** (notificações nativas cross-platform: Windows via WinRT, Linux via D-Bus)
- **pytest** (testes automatizados)

## Requisitos

- Python 3.12 ou superior
- Ambiente virtual Python `.venv`
- Windows 10/11 ou Linux com suporte a D-Bus (para notificações nativas completas)

## Como criar e ativar o ambiente virtual (Windows)

Usando PowerShell, no diretório do repositório:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Como instalar as dependências

```powershell
pip install -e ".[dev]"
```

## Como executar a aplicação

```powershell
# Modo recomendado (módulo Python)
python -m free_games_hub

# Ou via script definido no pyproject
free-games-hub
```

## Como rodar os testes

Todos os testes são **offline** (utilizam fixtures XML locais):

```powershell
pytest
```

## Onde os dados são armazenados

Os dados são salvos em um diretório de dados adequado ao sistema operacional, nunca no diretório de trabalho atual.

- **Windows:** `%APPDATA%\FreeGamesHub\` (normalmente `C:\Users\<SeuUsuario>\AppData\Roaming\FreeGamesHub\`)
- **Linux:** `~/.local/share/free-games-hub/`

O banco SQLite principal é:

- `free_games_hub.db`

O log da aplicação fica em `app.log` no mesmo diretório, com rotação automática. Quando há terminal, os logs também são exibidos nele. Não são gerados arquivos `.env` nem dados sensíveis.

Na primeira execução após a renomeação de *Steam Free Games Monitor* para *Free Games Hub*, o banco antigo (`%APPDATA%\SteamFreeGamesMonitor\steam_free_games_monitor.db`) é copiado automaticamente para o novo diretório, preservando histórico, configurações e filtros.

Para forçar um diretório diferente (útil em testes):

```powershell
$env:FGH_DATA_DIR = "C:\temp\test-fgh"
python -m free_games_hub
```

## Aparência e tela de abertura

- **Barra de título escura:** no Windows, a janela usa a API nativa DWM para deixar a barra de título com o mesmo tom do tema (`#0b0f17`), preservando botões, cantos arredondados, Snap Layouts e arrasto nativos.
- **Splash screen:** ao abrir (fora do modo `--hidden`), a aplicação exibe uma logo flutuante com fundo transparente por cerca de 3 segundos e então revela o painel principal com transição suave. Um clique na splash pula a espera.
- **Arquivo da splash:** coloque a imagem PNG com transparência em `packaging\assets\splash.png` (usada no build) ou em `src\free_games_hub\assets\splash.png` (lida direto em modo desenvolvimento). Se o arquivo não existir, a aplicação usa o ícone padrão (`app.png`) como fallback.
- **Ícone do app:** a fonte é `packaging\assets\app.png`; depois de trocá-la, execute `& ".\.venv\Scripts\python.exe" .\packaging\generate_icon.py` para regenerar os `.ico` e sincronizar `src\free_games_hub\assets\`.

## Como adicionar novos feeds RSS

1. Abra a aplicação
2. Acesse a aba **Grupos RSS** no painel lateral
3. Clique em **Adicionar**
4. Informe o nome do grupo e a URL completa do feed RSS (ex.: `https://steamcommunity.com/groups/<grupo>/rss/`)
5. O grupo será cadastrado e, ao ser ativado, passará a ser monitorado nas verificações automáticas

O feed `https://steamcommunity.com/groups/jogosbra/rss/` (**Comunidade Jogos Brasil**) é **cadastrado automaticamente** na primeira execução caso ainda não exista.

## Estratégia de inicialização e detecção de novidades

- **Identificador único:** o `guid` do item é utilizado como identificador principal. Caso não exista, utiliza-se o `link` do anúncio. Caso também esteja ausente, um hash baseado em `título + data de publicação` é usado como identificador de fallback (`hash:...`).
- **Primeira leitura bem-sucedida de cada feed:** todos os itens com título contendo `[FREE]` são **importados para o histórico**, porém **nenhuma notificação retroativa** é enviada. Neste momento, o grupo é marcado como **inicializado**.
- **Verificações seguintes:** apenas itens não vistos (identificador ainda inexistente) são considerados **novos**. Somente esses novos itens são passíveis de notificação e são marcados como `notified=0` até serem processados pelo serviço de notificações.
- **Falha na primeira consulta:** se a primeira tentativa de baixar/interpretar o feed falhar (rede, HTTP inválido ou XML inválido), **o grupo NÃO é marcado como inicializado**. O erro é registrado e a verificação será reavaliada nas próximas rodadas.
- **Tolerância a falhas:** um único grupo com erro não interrompe a verificação dos demais grupos ativos.
- **Proteção contra concorrência:** não é possível iniciar uma nova verificação (automática ou manual) enquanto outra estiver em andamento (solicitações concorrentes são ignoradas).
- **Preferências:** notificações podem ser habilitadas/desabilitadas na aba **Configurações**.

## Seleção de Lojas e Filtros Avançados

Na aba **Configurações**, você pode personalizar detalhadamente a captura de ofertas:

- **Habilitar GamerPower API:** ativa ou desativa globalmente a consulta à API multi-loja.
- **Seleção de Lojas:** marque individualmente as lojas de interesse:
  * Steam
  * Epic Games Store
  * GOG
  * Itch.io
  * Ubisoft Connect
  * Battle.net
  * EA App (Origin)
  * Prime Gaming
  * Smilegate Stove
  * VR (Realidade Virtual)
  * DRM-Free
  * PC (Outros)
  * PlayStation (PS4 / PS5)
  * Xbox (Xbox One / Xbox Series X|S)
  * Nintendo Switch
  * Mobile (Android / iOS)
  * Ofertas com plataforma genérica (`PC`) são refinadas por título e URL, permitindo detectar lojas como Stove, Prime Gaming, Ubisoft e Battle.net.
- **Tipos de Ofertas:**
  * Jogos completos
  * DLCs e Itens / Moedas
  * Betas e Acesso antecipado
- **Filtro de Prazo:** opção de ignorar ofertas permanentes ou sem prazo definido (`end_date = "N/A"`).
- **Deduplicação Inteligente:** ofertas que aparecem em múltiplos locais (ex.: grupo da Steam e na GamerPower) são unificadas pelo ID canônico (`steam:app:{id}`) ou chave de loja/título, evitando alertas repetidos. Se uma oferta já cadastrada tiver seu prazo estendido, a data de término é atualizada silenciosamente.

## Validade das ofertas (ainda está grátis?)

Cada publicação é conferida na loja da Steam para saber se a oferta continua com **100% de desconto**:

- **Posts com link** `store.steampowered.com/app/{id}`: consulta direta aos detalhes do aplicativo.
- **Posts sem link**: busca pelo título na loja, aceitando apenas correspondência confiável (ignora `[FREE]`, caixa, acentos e pontuação).
- **Status exibidos:** `Grátis (-100%)`, `Expirado` (com preço atual e desconto), `F2P (não é promoção)` e `Não verificado`.
- O **Painel** mostra somente ofertas ainda grátis; o **Histórico** mostra tudo e permite filtrar por status.
- **Rechecagem:** ofertas grátis a cada 30 min; não verificadas a cada 6 h; demais a cada 24 h. Posts nunca verificados são conferidos na primeira rodada. O botão **Verificar preços** no Histórico força a atualização.
- Limite de 15 consultas por rodada, com intervalo entre requisições para não sobrecarregar a loja.

## Notificações nativas

- Cada oferta é notificada **somente depois de confirmada com 100% de desconto** na loja Steam.
- A notificação mostra o título limpo (sem `[FREE]`) e o grupo; ao clicar, abre a loja ou a publicação original.
- Falhas de envio aparecem em **Configurações → Erros recentes**. Use o botão **Testar notificação** para verificar permissões e o funcionamento do sistema.
- No Windows, permita notificações para o aplicativo e desative temporariamente o **Não Perturbe/Focus Assist** se nada aparecer.
- Quando as notificações estão desabilitadas, as ofertas pendentes são descartadas sem envio para evitar uma enxurrada ao reativar a preferência.

## Segundo plano e inicialização com o Windows

- **Fechar (X)** esconde a janela e mantém o monitor rodando no ícone da bandeja; **minimizar** continua normal.
- O menu da bandeja oferece **Abrir painel**, **Verificar agora**, **Notificações** e **Sair**.
- Abrir o programa novamente enquanto ele está na bandeja foca a janela existente, sem criar uma segunda instância.
- Em **Configurações**, a opção **Iniciar com o Windows (minimizado na bandeja)** cria uma entrada em `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` para o usuário atual, sem exigir administrador. O app é iniciado com `--hidden`.
- Desmarcar a opção remove a entrada. Se o aplicativo for movido para outro caminho, desmarque e marque novamente para atualizar o caminho.
- A opção de inicialização automática está disponível apenas no Windows nesta versão.

## Limitações conhecidas

- Filtro: apenas `[FREE]` no título (sem diferenciação entre giveaways temporários, jogos gratuitos permanentes ou outros tipos). A validade é conferida depois, consultando a loja.
- A verificação de validade usa a API não documentada da loja Steam (região Brasil). Mudanças ou limites de acesso podem fazer ofertas aparecerem como **Não verificado**.
- Posts sem link de loja e sem correspondência exata de título permanecem como **Não verificado**; o status pode ficar até 30 minutos defasado para ofertas ativas.
- Dependente da disponibilidade do feed RSS do Steam Group (quando o feed fica indisponível, histórico é preservado).
- No Linux, notificações nativas dependem do serviço D-Bus `org.freedesktop.Notifications`. Caso indisponível, a aplicação **não simula** notificações bem-sucedidas: registra a limitação e mantém histórico/alertas na própria interface.
- A bandeja do sistema depende do ambiente gráfico. Se não estiver disponível, fechar a janela encerra o aplicativo normalmente.
- Notificações podem ser silenciadas pelo sistema operacional (Não Perturbe/Focus Assist) mesmo com o app configurado corretamente.
- Alguns ambientes podem ter políticas que bloqueiem a abertura de URLs via `QDesktopServices.openUrl` (o comportamento varia conforme SO e gerenciador de janelas).

## Instalador Windows

O instalador é gerado com **PyInstaller** (build `onedir`) e **Inno Setup 6**. A instalação é por usuário, em `%LOCALAPPDATA%\Programs\FreeGamesHub`, sem exigir administrador. O aplicativo instalado não precisa de Python nem de Qt na máquina.

### Requisitos de build (somente na máquina de desenvolvimento)

```powershell
# Dependências Python de build (PyInstaller e Pillow)
pip install -e ".[build]"

# Inno Setup 6 (uma vez)
winget install --id JRSoftware.InnoSetup -e
```

### Gerar executável e instalador

```powershell
.\packaging\build.ps1
```

O script executa os testes, gera o ícone, cria os metadados de versão, roda o PyInstaller e compila o instalador. Saídas:

- `dist\FreeGamesHub\FreeGamesHub.exe`
- `dist\FreeGamesHub-Setup-<versão>.exe`

Para gerar apenas o executável durante o desenvolvimento:

```powershell
.\packaging\build.ps1 -SkipTests -SkipInstaller
```

### Comportamento do instalador

- Atalho no Menu Iniciar; atalho opcional na área de trabalho.
- Opção de abrir o aplicativo ao final da instalação.
- A instalação por cima de uma versão anterior preserva o banco em `%APPDATA%\FreeGamesHub\` e atualiza o executável.
- Ao atualizar a partir do antigo *Steam Free Games Monitor*, o instalador encerra a instância antiga, migra a entrada de autostart e remove a pasta antiga em `%LOCALAPPDATA%\Programs\SteamFreeGamesMonitor`.
- A desinstalação remove atalhos, arquivos, a entrada de autostart e o próprio aplicativo, mas **preserva o banco e os logs** em `%APPDATA%\FreeGamesHub\`.
- O autostart é desligado por padrão; marque a opção nas Configurações para ativar.
- O instalador atual não é assinado digitalmente. Na primeira execução, o Windows pode exibir o aviso do SmartScreen; use **Mais informações → Executar assim mesmo** ao instalar o próprio build.
- Caso o app esteja aberto durante uma atualização ou desinstalação, o instalador solicita o encerramento via `--quit` antes de substituir os arquivos.

### Observações técnicas

- O build é `onedir` em vez de `--onefile` para iniciar mais rápido, reduzir falsos positivos de antivírus e simplificar atualizações.
- O `desktop-notifier` usa WinRT no Windows; o spec do PyInstaller inclui os módulos nativos necessários e os recursos padrão da biblioteca.
- O executável é `windowed`; por isso, o diagnóstico fica em `%APPDATA%\FreeGamesHub\app.log`.
- Não há suporte a empacotamento para macOS nesta versão.

## Comandos rápidos (resumo)

| Ação | Comando (PowerShell) |
|---|---|
| Criar ambiente virtual | `py -3.12 -m venv .venv` |
| Ativar ambiente | `.\.venv\Scripts\Activate.ps1` |
| Instalar dependências | `pip install -e ".[dev]"` |
| Executar aplicação | `python -m free_games_hub` |
| Executar testes | `pytest` |