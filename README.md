# Free Games Hub

[![CI](https://github.com/Marcospena12/free-games-alert/actions/workflows/ci.yml/badge.svg)](https://github.com/Marcospena12/free-games-alert/actions/workflows/ci.yml)
[![Release](https://github.com/Marcospena12/free-games-alert/actions/workflows/release.yml/badge.svg)](https://github.com/Marcospena12/free-games-alert/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Electron](https://img.shields.io/badge/electron-45-blue.svg)](desktop/package.json)

Monitor de jogos gratuitos com suporte a feeds RSS da comunidade Steam e integração multi-loja via GamerPower API (Steam, Epic Games Store, GOG, Itch.io, Ubisoft Connect, Battle.net, EA App, Prime Gaming, DRM-Free, Consoles e Mobile). Focado em simplicidade, confiabilidade e portabilidade entre Windows e Linux.

## Arquitetura (0.3+)

A partir da 0.3.0 o aplicativo é composto por três camadas:

- **Frontend (Electron + React + TypeScript):** janela, splash, bandeja do sistema, autostart, notificações de shell e navegação. O renderer é uma SPA (Vite/Tailwind) servida pelo próprio backend na mesma origem.
- **Backend (FastAPI + uvicorn, empacotado com PyInstaller):** roda em `127.0.0.1` em porta aleatória, com autenticação por token. É dono do agendamento de verificações, da persistência SQLite (schema v4) e da API REST + WebSocket usada pela interface.
- **Núcleo Python (inalterado):** o mesmo código testado das versões 0.2.x (feeds RSS, GamerPower, deduplicação, verificação de preços, notificações) agora é exposto via API em vez de ser acionado diretamente pela UI.

O processo Electron inicia o backend como filho, lê a porta real do stdout (`FGH_PORT=<n>`) e fecha ambos juntos. A interface PySide6 continua no repositório como legado, mas **não** faz parte do app empacotado.

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

- **Python 3.12+** (backend e núcleo de monitoramento)
- **FastAPI + uvicorn** (API local do app)
- **Electron 45 + React 18 + TypeScript** (interface desktop)
- **electron-vite / Vite 5** (build da SPA)
- **electron-builder** (instaladores NSIS no Windows, AppImage/deb no Linux)
- **PyInstaller** (empacotamento do backend headless)
- **feedparser** (leitura e análise de feeds RSS/Atom)
- **sqlite3** (persistência local, via módulo padrão, Schema v4)
- **desktop-notifier** (notificações nativas cross-platform: Windows via WinRT, Linux via D-Bus)
- **pytest** (testes automatizados)

## Requisitos

- **Para usar:** Windows 10/11 x64 ou Linux x64 (instale o pacote correspondente).
- **Para desenvolver:** Python 3.12+, Node.js 20+ (recomendado 24+), ambiente virtual Python `.venv`.
- Linux com D-Bus para notificações nativas completas.

## Como desenvolver

### Ambiente Python (backend)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,build]"
```

### Rodar o backend standalone (opcional)

```powershell
python -m free_games_hub.api
```

O backend imprime a porta escolhida no stdout (`FGH_PORT=<n>`).

### Rodar a interface (modo desenvolvimento)

```powershell
cd desktop
npm install
npm run dev
```

### Rodar os testes

Todos os testes são **offline** (utilizam fixtures XML locais):

```powershell
pytest
```

### Build local do app completo (SPA + backend + instalador)

```powershell
python scripts/build_desktop.py            # testes + build completo
python scripts/build_desktop.py --skip-tests
python scripts/build_desktop.py --skip-tests --skip-installer   # só SPA + backend-dist
```

O script:
1. valida que `pyproject.toml` e `desktop/package.json` estão na mesma versão;
2. compila a SPA com `electron-vite`;
3. empacota o backend com PyInstaller (onedir, console);
4. monta `backend-dist/` (backend + SPA + assets de runtime);
5. roda o `electron-builder` para a plataforma atual.

Saídas em `desktop/dist/`:

- Windows: `FreeGamesHub-Setup-<versão>.exe` (NSIS)
- Linux: `FreeGamesHub-<versão>-x64.AppImage` e `FreeGamesHub-<versão>-x64.deb`

> O build de Linux (AppImage/deb) deve rodar em Linux; no Windows só o instalador NSIS é gerado.

## Releases

As releases são geradas automaticamente no **GitHub Actions** ao publicar uma tag `v<versão>`:

- `ci.yml` — testes Python + typecheck/build do desktop em cada push/PR.
- `release.yml` — em tag: testes, build Windows (NSIS) em `windows-latest`, build Linux (AppImage/deb) em `ubuntu-22.04`, geração de `SHA256SUMS.txt` e publicação da Release com todos os artefatos. Também pode ser disparado manualmente (`workflow_dispatch`) em modo *dry-run* (só gera artefatos, sem publicar).

O instalador **não é assinado digitalmente**. Na primeira execução o Windows pode exibir o aviso do SmartScreen; use **Mais informações → Executar assim mesmo**.

## Instalador Windows (NSIS)

- Instalação por usuário em `%LOCALAPPDATA%\Programs\Free Games Hub`, sem exigir administrador.
- Atalho no Menu Iniciar e (opcional) na área de trabalho; opção de abrir o app ao final.
- **Migração da 0.2.0 (Inno Setup):** ao instalar por cima da versão antiga, o instalador:
  1. encerra o processo antigo (`FreeGamesHub.exe`);
  2. faz um backup único do banco (`free_games_hub.pre-0.3.0.db`) no diretório de dados;
  3. desinstala silenciosamente a versão 0.2.0 (`%LOCALAPPDATA%\Programs\FreeGamesHub`);
  4. migra a entrada de autostart do valor legado `FreeGamesHub`/`SteamFreeGamesMonitor` para o novo `Free Games Hub`.
- A desinstalação remove atalhos, arquivos e a entrada de autostart, mas **preserva o banco e os logs** em `%APPDATA%\FreeGamesHub\`.
- Se o app estiver aberto durante a atualização, o instalador solicita o encerramento antes de substituir os arquivos.

## Onde os dados são armazenados

Os dados são salvos em um diretório de dados adequado ao sistema operacional, nunca no diretório de trabalho atual.

- **Windows:** `%APPDATA%\FreeGamesHub\` (normalmente `C:\Users\<SeuUsuario>\AppData\Roaming\FreeGamesHub\`)
- **Linux:** `~/.local/share/free-games-hub/`

O banco SQLite principal é `free_games_hub.db` (schema v4, compatível com as versões 0.2.x — **nenhuma migração foi necessária** na 0.3.0). O log da aplicação fica em `app.log` no mesmo diretório, com rotação automática. Não são gerados arquivos `.env` nem dados sensíveis.

Na primeira execução após a renomeação de *Steam Free Games Monitor* para *Free Games Hub*, o banco antigo (`%APPDATA%\SteamFreeGamesMonitor\steam_free_games_monitor.db`) é copiado automaticamente para o novo diretório, preservando histórico, configurações e filtros.

Para forçar um diretório diferente (útil em testes):

```powershell
$env:FGH_DATA_DIR = "C:\temp\test-fgh"
python -m free_games_hub.api
```

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
- **Filtro visual por loja:** os "chips" de loja no topo do Painel filtram a visualização no cliente, sem alterar o monitoramento.

## Validade das ofertas (ainda está grátis?)

Cada publicação é conferida na loja da Steam para saber se a oferta continua com **100% de desconto**:

- **Posts com link** `store.steampowered.com/app/{id}`: consulta direta aos detalhes do aplicativo.
- **Posts sem link**: busca pelo título na loja, aceitando apenas correspondência confiável (ignora `[FREE]`, caixa, acentos e pontuação).
- **Status exibidos:** `Grátis (-100%)`, `Expirado` (com preço atual e desconto), `F2P (não é promoção)` e `Não verificado`.
- O **Painel** mostra somente ofertas ainda grátis (`status=free`, prazo ativo e `in_library=0`); o **Histórico** mostra tudo e permite filtrar por status.
- **Rechecagem:** ofertas grátis a cada 30 min; não verificadas a cada 6 h; demais a cada 24 h. Posts nunca verificados são conferidos na primeira rodada. O botão **Verificar preços** no Histórico força a atualização.
- Limite de 15 consultas por rodada, com intervalo entre requisições para não sobrecarregar a loja.

## Notificações nativas

- Cada oferta é notificada **somente depois de confirmada com 100% de desconto** na loja Steam.
- A notificação mostra o título limpo (sem `[FREE]`) e o grupo; ao clicar, abre a loja ou a publicação original.
- Falhas de envio aparecem em **Configurações → Erros recentes**. Use o botão **Testar notificação** para verificar permissões e o funcionamento do sistema.
- No Windows, permita notificações para o aplicativo e desative temporariamente o **Não Perturbe/Focus Assist** se nada aparecer.
- Quando as notificações estão desabilitadas, as ofertas pendentes são descartadas sem envio para evitar uma enxurrada ao reativar a preferência.

## Segundo plano e inicialização com o sistema

- **Fechar (X)** esconde a janela e mantém o monitor rodando no ícone da bandeja; **minimizar** continua normal. Se a bandeja não estiver disponível no ambiente, fechar encerra o app normalmente.
- O menu da bandeja oferece **Abrir painel**, **Verificar agora**, **Notificações** e **Sair**.
- Abrir o programa novamente enquanto ele está na bandeja foca a janela existente, sem criar uma segunda instância.
- Em **Configurações**, a opção **Iniciar com o sistema (minimizado na bandeja)** cria uma entrada de autostart para o usuário atual, sem exigir administrador, e inicia o app com `--hidden`:
  - **Windows:** valor `Free Games Hub` em `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (as entradas legadas `FreeGamesHub` e `SteamFreeGamesMonitor` são removidas automaticamente).
  - **Linux:** arquivo `.desktop` em `~/.config/autostart/`.
- Desmarcar a opção remove a entrada. Se o aplicativo for movido para outro caminho, desmarque e marque novamente para atualizar o caminho.

## Limitações conhecidas

- Filtro: apenas `[FREE]` no título (sem diferenciação entre giveaways temporários, jogos gratuitos permanentes ou outros tipos). A validade é conferida depois, consultando a loja.
- A verificação de validade usa a API não documentada da loja Steam (região Brasil). Mudanças ou limites de acesso podem fazer ofertas aparecerem como **Não verificado**.
- Posts sem link de loja e sem correspondência exata de título permanecem como **Não verificado**; o status pode ficar até 30 minutos defasado para ofertas ativas.
- Dependente da disponibilidade do feed RSS do Steam Group (quando o feed fica indisponível, histórico é preservado).
- No Linux, notificações nativas dependem do serviço D-Bus `org.freedesktop.Notifications`. Caso indisponível, a aplicação **não simula** notificações bem-sucedidas: registra a limitação e mantém histórico/alertas na própria interface.
- A bandeja do sistema depende do ambiente gráfico. Se não estiver disponível, fechar a janela encerra o aplicativo normalmente.
- Notificações podem ser silenciadas pelo sistema operacional (Não Perturbe/Focus Assist) mesmo com o app configurado corretamente.
- Os pacotes **não são assinados digitalmente**; o SmartScreen/aviso equivalente pode aparecer na primeira execução.
- Não há suporte a empacotamento para macOS nesta versão.

## Comandos rápidos (resumo)

| Ação | Comando (PowerShell) |
|---|---|
| Criar ambiente virtual | `py -3.12 -m venv .venv` |
| Ativar ambiente | `.\.venv\Scripts\Activate.ps1` |
| Instalar dependências (dev + build) | `pip install -e ".[dev,build]"` |
| Executar testes | `pytest` |
| Backend standalone | `python -m free_games_hub.api` |
| Interface (dev) | `cd desktop; npm install; npm run dev` |
| Build completo local | `python scripts/build_desktop.py` |
| Build sem instalador | `python scripts/build_desktop.py --skip-tests --skip-installer` |
| Instalador Windows | `cd desktop; npm run dist:win` |
| Typecheck/build do desktop | `cd desktop; npm run typecheck; npm run build` |
