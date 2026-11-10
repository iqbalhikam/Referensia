#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};

enum Backend {
    Dev(Child),
    Sidecar(CommandChild),
}

impl Backend {
    fn kill(self) {
        match self {
            Backend::Dev(mut c) => {
                let _ = c.kill();
                let _ = c.wait();
            }
            Backend::Sidecar(c) => {
                let pid = c.pid();
                let _ = c.kill();
                // Jangan biarkan exe sidecar terkunci saat penginstal menimpanya.
                #[cfg(windows)]
                {
                    // /T: PyInstaller onefile memakai proses induk + anak; keduanya harus mati.
                    std::thread::sleep(std::time::Duration::from_millis(300));
                    let _ = Command::new("taskkill")
                        .args(["/PID", &pid.to_string(), "/T", "/F"])
                        .output();
                }
                #[cfg(not(windows))]
                let _ = pid;
            }
        }
    }
}

struct BackendState(Mutex<Option<Backend>>);

fn hentikan_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendState>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(b) = guard.take() {
                b.kill();
            }
        }
    }
}

fn spawn_dev() -> Option<Child> {
    let backend_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend");
    let venv_python = backend_dir.join(".venv/Scripts/python.exe");
    let python = if venv_python.exists() {
        venv_python
    } else {
        PathBuf::from("python")
    };
    Command::new(python)
        .arg("server.py")
        .current_dir(&backend_dir)
        .spawn()
        .ok()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let backend = if cfg!(debug_assertions) {
                spawn_dev().map(Backend::Dev)
            } else {
                let app_exe = std::env::current_exe()
                    .ok()
                    .and_then(|p| p.file_name().map(|n| n.to_string_lossy().into_owned()))
                    .unwrap_or_else(|| "referensia-desktop.exe".to_string());
                app.shell()
                    .sidecar("referensia-server")
                    .ok()
                    .and_then(|cmd| cmd.env("REFERENSIA_APP_EXE", &app_exe).spawn().ok())
                    .map(|(_, child)| Backend::Sidecar(child))
            };
            if backend.is_none() {
                eprintln!("[Referensia] gagal menjalankan backend — UI tampil dengan peringatan");
            }
            app.manage(BackendState(Mutex::new(backend)));
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                hentikan_backend(window.app_handle());
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                hentikan_backend(app);
            }
        });
}