# Steam Free Games Monitor

Monitor de feeds RSS da comunidade Steam para identificar publicações relacionadas a jogos gratuitos e notificar o usuário. Focado em simplicidade, confiabilidade e portabilidade entre Windows e Linux.

## Objetivo

O Steam Free Games Monitor monitora feeds RSS de grupos da comunidade Steam, identifica novas publicações cujo título contenha `[FREE]` e notifica o usuário. A aplicação é puramente desktop, não depende de n8n, servidores remotos, serviços pagos ou APIs de IA.

## Tecnologias utilizadas

- **Python 3.12+**
- **PySide6** (interface desktop Qt)
- **feedparser** (leitura e análise de feeds RSS/Atom)
- **sqlite3** (persistência local, via módulo padrão)
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
python -m steam_free_games_monitor

# Ou via script definido no pyproject
steam-free-games-monitor
```

## Como rodar os testes

Todos os testes são **offline** (utilizam fixtures XML locais):

```powershell
pytest
```

## Onde os dados são armazenados

Os dados são salvos em um diretório de dados adequado ao sistema operacional, nunca no diretório de trabalho atual.

- **Windows:** `%APPDATA%\SteamFreeGamesMonitor\` (normalmente `C:\Users\<SeuUsuario>\AppData\Roaming\SteamFreeGamesMonitor\`)
- **Linux:** `~/.local/share/steam-free-games-monitor/`

O banco SQLite principal é:

- `steam_free_games_monitor.db`

O log da aplicação fica em `app.log` no mesmo diretório, com rotação automática. Quando há terminal, os logs também são exibidos nele. Não são gerados arquivos `.env` nem dados sensíveis.

Para forçar um diretório diferente (útil em testes):

```powershell
$env:SFGM_DATA_DIR = "C:\temp\test-sfgm"
python -m steam_free_games_monitor
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

O instalador é gerado com **PyInstaller** (build `onedir`) e **Inno Setup 6**. A instalação é por usuário, em `%LOCALAPPDATA%\Programs\SteamFreeGamesMonitor`, sem exigir administrador. O aplicativo instalado não precisa de Python nem de Qt na máquina.

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

- `dist\SteamFreeGamesMonitor\SteamFreeGamesMonitor.exe`
- `dist\SteamFreeGamesMonitor-Setup-<versão>.exe`

Para gerar apenas o executável durante o desenvolvimento:

```powershell
.\packaging\build.ps1 -SkipTests -SkipInstaller
```

### Comportamento do instalador

- Atalho no Menu Iniciar; atalho opcional na área de trabalho.
- Opção de abrir o aplicativo ao final da instalação.
- A instalação por cima de uma versão anterior preserva o banco em `%APPDATA%\SteamFreeGamesMonitor\` e atualiza o executável.
- A desinstalação remove atalhos, arquivos, a entrada de autostart e o próprio aplicativo, mas **preserva o banco e os logs** em `%APPDATA%\SteamFreeGamesMonitor\`.
- O autostart é desligado por padrão; marque a opção nas Configurações para ativar.
- O instalador atual não é assinado digitalmente. Na primeira execução, o Windows pode exibir o aviso do SmartScreen; use **Mais informações → Executar assim mesmo** ao instalar o próprio build.
- Caso o app esteja aberto durante uma atualização ou desinstalação, o instalador solicita o encerramento via `--quit` antes de substituir os arquivos.

### Observações técnicas

- O build é `onedir` em vez de `--onefile` para iniciar mais rápido, reduzir falsos positivos de antivírus e simplificar atualizações.
- O `desktop-notifier` usa WinRT no Windows; o spec do PyInstaller inclui os módulos nativos necessários e os recursos padrão da biblioteca.
- O executável é `windowed`; por isso, o diagnóstico fica em `%APPDATA%\SteamFreeGamesMonitor\app.log`.
- Não há suporte a empacotamento para macOS nesta versão.

## Comandos rápidos (resumo)

| Ação | Comando (PowerShell) |
|---|---|
| Criar ambiente virtual | `py -3.12 -m venv .venv` |
| Ativar ambiente | `.\.venv\Scripts\Activate.ps1` |
| Instalar dependências | `pip install -e ".[dev]"` |
| Executar aplicação | `python -m steam_free_games_monitor` |
| Executar testes | `pytest` |