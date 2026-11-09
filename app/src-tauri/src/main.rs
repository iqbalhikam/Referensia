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
                let _ = c.kill();
            }
        }
    }
}

struct BackendState(Mutex<Option<Backend>>);

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
                app.shell()
                    .sidecar("referensia-server")
                    .ok()
                    .and_then(|cmd| cmd.spawn().ok())
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
                if let Some(state) = window.try_state::<BackendState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(b) = guard.take() {
                            b.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}