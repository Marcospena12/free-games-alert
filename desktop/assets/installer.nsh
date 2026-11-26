; Migração 0.2.0 (PySide6/Inno Setup) -> 0.3.x (Electron/NSIS).
;
; Este include é compilado dentro do instalador gerado pelo electron-builder.
; A pasta de dados do usuário (%APPDATA%\FreeGamesHub) NUNCA é removida.

!define FGH_RUN_KEY "Software\Microsoft\Windows\CurrentVersion\Run"
!define FGH_INSTALLER_KEY "Software\FreeGamesHub"
!define FGH_LEGACY_DIR "$LOCALAPPDATA\Programs\FreeGamesHub"
!define FGH_LEGACY_UNINSTALLER "$LOCALAPPDATA\Programs\FreeGamesHub\unins000.exe"

!macro customInit
  ; Encerra instâncias antigas e a própria versão Electron antes de trocar
  ; arquivos. O taskkill é silencioso e não falha se o processo não existir.
  nsExec::ExecToLog 'taskkill /IM FreeGamesHub.exe /T /F'
  Pop $0
  nsExec::ExecToLog 'taskkill /IM free-games-hub.exe /T /F'
  Pop $0

  ; Guarda a preferência de autostart da 0.2.0 antes de o desinstalador
  ; antigo apagar o valor legado do registro.
  ReadRegStr $0 HKCU "${FGH_RUN_KEY}" "FreeGamesHub"
  StrCmp $0 "" 0 fgh_legacy_autostart
  ReadRegStr $0 HKCU "${FGH_RUN_KEY}" "SteamFreeGamesMonitor"
  StrCmp $0 "" fgh_no_legacy_autostart

  fgh_legacy_autostart:
    WriteRegStr HKCU "${FGH_INSTALLER_KEY}" "LegacyAutostart" "1"

  fgh_no_legacy_autostart:

  ; Cópia de segurança única do banco antes da primeira execução da 0.3.
  IfFileExists "$APPDATA\FreeGamesHub\free_games_hub.pre-0.3.0.db" fgh_backup_done
  IfFileExists "$APPDATA\FreeGamesHub\free_games_hub.db" 0 fgh_backup_done
    CopyFiles /SILENT "$APPDATA\FreeGamesHub\free_games_hub.db" "$APPDATA\FreeGamesHub\free_games_hub.pre-0.3.0.db"
  fgh_backup_done:

  ; Desinstala a 0.2.0 silenciosamente (o banco em %APPDATA% é preservado).
  IfFileExists "${FGH_LEGACY_UNINSTALLER}" 0 fgh_legacy_uninstall_done
    ExecWait '"${FGH_LEGACY_UNINSTALLER}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $0
    RMDir /r "${FGH_LEGACY_DIR}"
  fgh_legacy_uninstall_done:

  DeleteRegValue HKCU "${FGH_RUN_KEY}" "FreeGamesHub"
  DeleteRegValue HKCU "${FGH_RUN_KEY}" "SteamFreeGamesMonitor"
!macroend

!macro customInstall
  ; Preserva o autostart que o usuário já tinha, agora apontando para o
  ; executável novo. Também atualiza o caminho em upgrades da própria 0.3.
  ReadRegStr $0 HKCU "${FGH_RUN_KEY}" "Free Games Hub"
  StrCmp $0 "" 0 fgh_update_new_autostart
  ReadRegStr $0 HKCU "${FGH_INSTALLER_KEY}" "LegacyAutostart"
  StrCmp $0 "1" 0 fgh_autostart_done

  fgh_update_new_autostart:
    WriteRegStr HKCU "${FGH_RUN_KEY}" "Free Games Hub" '"$INSTDIR\free-games-hub.exe" --hidden'

  fgh_autostart_done:
    DeleteRegValue HKCU "${FGH_INSTALLER_KEY}" "LegacyAutostart"
!macroend

!macro customUnInstall
  ; Encerra o app para liberar arquivos e remove as entradas de autostart.
  nsExec::ExecToLog 'taskkill /IM free-games-hub.exe /T /F'
  Pop $0
  DeleteRegValue HKCU "${FGH_RUN_KEY}" "Free Games Hub"
  DeleteRegValue HKCU "${FGH_RUN_KEY}" "FreeGamesHub"
  DeleteRegValue HKCU "${FGH_RUN_KEY}" "SteamFreeGamesMonitor"
  DeleteRegValue HKCU "${FGH_INSTALLER_KEY}" "LegacyAutostart"
!macroend
