pub mod daemon;

use daemon::{DaemonManager, DaemonStatus, DEFAULT_DAEMON_PORT};
use std::path::PathBuf;
use tauri::{Manager, RunEvent, State, WindowEvent};

#[tauri::command]
fn get_daemon_status(state: State<DaemonManager>) -> DaemonStatus {
    state.get_status()
}

#[tauri::command]
fn start_daemon(state: State<DaemonManager>, app: tauri::AppHandle) -> Result<DaemonStatus, String> {
    // Determine repository root or application resource path
    let repo_root = app
        .path()
        .resource_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."));

    state.ensure_started(&repo_root)
}

#[tauri::command]
fn terminate_daemon(state: State<DaemonManager>) -> Result<bool, String> {
    state.terminate();
    Ok(true)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let daemon_manager = DaemonManager::new(DEFAULT_DAEMON_PORT);

    let app = tauri::Builder::default()
        .manage(daemon_manager)
        .invoke_handler(tauri::generate_handler![
            get_daemon_status,
            start_daemon,
            terminate_daemon
        ])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::Destroyed = event {
                eprintln!("[FinTrace] Main window destroyed. Cleaning up child processes...");
                let manager = window.state::<DaemonManager>();
                manager.terminate();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| match event {
        RunEvent::ExitRequested { .. } | RunEvent::Exit => {
            eprintln!("[FinTrace] Application exit event received. Ensuring 0 zombie processes...");
            let manager = app_handle.state::<DaemonManager>();
            manager.terminate();
        }
        _ => {}
    });
}
