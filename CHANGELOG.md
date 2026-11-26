# Changelog

Todas as mudanças relevantes do Free Games Hub estão documentadas neste arquivo.

## [0.3.1] — 2026-11-26

### Alterado
- **Nova logo** do aplicativo (controle roxo) em janela, bandeja, instalador e atalhos.
- **Geração de ícones centralizada**: a logo é recortada nas bordas transparentes e centralizada em um quadrado, mantendo a proporção e melhorando a legibilidade em tamanhos pequenos; PNGs salvos com compressão máxima.

## [0.3.0] — 2026-11-26

### Adicionado
- **Nova interface Electron + React + TypeScript** (SPA Vite/Tailwind) substituindo a interface PySide6:
  - **Painel** — somente ofertas gratuitas no momento (`status=free`, prazo ativo e não na biblioteca), com chips de filtro por loja (filtro visual no cliente).
  - **Histórico** — todas as ofertas com filtro por status e botão **Verificar preços** para forçar a revalidação.
  - **Grupos RSS** — gestão completa dos feeds da comunidade Steam.
  - **Configurações** — lojas GamerPower, tipos de oferta, filtro de prazo, notificações, autostart, testar notificação e erros recentes.
  - Toasts e eventos em tempo real via **WebSocket** (novidades, verificação concluída, erros).
- **Backend local FastAPI + uvicorn** empacotado com PyInstaller (onedir, console):
  - Roda em `127.0.0.1` em porta aleatória com **autenticação por token** gerado a cada execução.
  - API REST + WebSocket servida na mesma origem da SPA (sem CORS em produção).
  - Endpoints: snapshot, histórico, grupos, configurações, lojas, sobre, verificação manual.
- **Autostart nativo** (sem administrador):
  - Windows: valor `Free Games Hub` em `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, com limpeza automática das entradas legadas `FreeGamesHub` e `SteamFreeGamesMonitor`.
  - Linux: arquivo `.desktop` em `~/.config/autostart/`.
- **Tray** (bandeja do sistema) com menu: abrir painel, verificar agora, notificações, sair. Fechar a janela esconde para a bandeja; segunda instância foca a janela existente.
- **Splash screen** e tratamento de erros nativo (se o backend falhar ao iniciar, a janela exibe o erro com ações).
- **Instalador Windows NSIS** com migração automática da 0.2.0 (Inno Setup):
  - Encerra o processo antigo, faz backup único do banco (`free_games_hub.pre-0.3.0.db`), desinstala silenciosamente a 0.2.0 e migra o autostart.
- **Builds Linux**: AppImage e `.deb` (x64) via electron-builder.
- **GitHub Actions**:
  - `ci.yml` — testes Python + typecheck/build do desktop em cada push/PR.
  - `release.yml` — em tag `v*`: testes, build Windows (NSIS) e Linux (AppImage/deb), `SHA256SUMS.txt` e publicação automática da Release (com modo *dry-run* manual).

### Alterado
- **Arquitetura**: o núcleo Python testado (feeds RSS, GamerPower, deduplicação, verificação de preços, notificações) foi mantido **inalterado** e agora é exposto via API em vez de ser acionado diretamente pela UI.
- **Painel** passa a exibir apenas ofertas genuinamente gratuitas no momento (antes, a lista misturava estados).
- `pyproject.toml`: versão `0.3.0`; novos extras `api` e `build`.
- `.github/workflows/ci.yml`: novo job `desktop` (Node 24, `npm ci`, typecheck, build).
- `README.md` reescrito para a arquitetura Electron.

### Removido
- Interface PySide6 **não faz mais parte do app empacotado** (o código permanece no repositório como legado, mas é excluído do backend PyInstaller).
- Empacotamento Inno Setup (substituído por NSIS).

### Corrigido
- `desktop/src/main/backend.ts` — guarda contra geração duplicada de token/porta.
- `desktop/src/main/autostart.ts` — escrita direta no registro (Windows) com limpeza de entradas legadas; `.desktop` no Linux.
- `desktop/src/main/index.ts` — segunda instância abre com `--hidden`, guarda contra encerramento duplo, `try/catch` na tray, fechar-para-bandeja somente quando a tray existe, criação do diretório de dados.
- `History.tsx` — botão **Verificar preços** funcional.
- `SettingsPage.tsx` — payload de save reduzido e `copyFilterToAll` cobre todos os slugs de `/api/stores`.
- Backend: `ensure_defaults`, fallback da SPA, docs desativados com token, API de configurações, `/api/stores`, `/api/about`, busca antes do `LIMIT`, `compare_digest` no token, `busy_timeout=5000`.

## [0.2.0] — legado

- Monitor de jogos gratuitos com feeds RSS da comunidade Steam + GamerPower API multi-loja.
- Interface PySide6, instalador Inno Setup (Windows), banco SQLite schema v4 em `%APPDATA%\FreeGamesHub`.
- Histórico, grupos RSS, configurações, notificações nativas e verificação de preços na loja Steam.
