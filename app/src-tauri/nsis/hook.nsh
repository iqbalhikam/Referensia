; Hentikan aplikasi & sidecar sebelum berkas .exe ditimpa.
; Sidecar PyInstaller memakai proses induk + anak, jadi wajib /T (tree kill).
!macro NSIS_HOOK_PREINSTALL
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM referensia-server.exe'
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM referensia-desktop.exe'
  Sleep 1500
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM referensia-server.exe'
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM referensia-desktop.exe'
  Sleep 800
!macroend
