mod commands;
mod history;
mod inference;

use commands::AppState;
use std::path::PathBuf;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let resource_dir = app.path().resource_dir()
                .unwrap_or_else(|_| PathBuf::from("."));

            // Embedded Python runtime (python-build-standalone)
            let python_bin = resource_dir.join("python-runtime/bin/python3");
            // Python scripts
            let python_dir = resource_dir.join("python");
            // ONNX models
            let model_dir = resource_dir.join("models");

            let data_dir = dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".marine_detecter");

            app.manage(AppState {
                python_bin,
                python_dir,
                model_dir,
                output_base: data_dir.join("runs"),
                history: crate::history::HistoryStore::new(data_dir.join("history")),
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::detect_rgb,
            commands::detect_multichannel,
            commands::get_history_list,
            commands::get_history_detail,
            commands::delete_history,
            commands::pick_file,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
