use crate::history::HistoryItem;
use crate::inference::{DetectionResult, ModelInfo};
use std::path::PathBuf;
use tauri::State;

pub struct AppState {
    pub python_bin: PathBuf,
    pub python_dir: PathBuf,
    pub model_dir: PathBuf,
    pub output_base: PathBuf,
    pub history: crate::history::HistoryStore,
}

#[tauri::command]
pub async fn detect_rgb(
    state: State<'_, AppState>,
    image_path: String,
    model_names: Vec<String>,
) -> Result<DetectionResult, String> {
    let run_id = uuid::Uuid::new_v4().to_string();
    let output_dir = state.output_base.join(&run_id);
    std::fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;

    let model_paths: Vec<String> = model_names
        .iter()
        .map(|name| {
            state.model_dir
                .join("rgb")
                .join(format!("{}.onnx", name))
                .to_string_lossy()
                .to_string()
        })
        .collect();

    let result = crate::inference::run_inference(
        &image_path,
        output_dir.to_str().unwrap(),
        &state.python_bin,
        &state.python_dir,
        &model_paths,
        "rgb",
    )?;

    let file_name = std::path::Path::new(&image_path)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string());

    state.history.add(&result, &file_name);

    Ok(result)
}

#[tauri::command]
pub async fn detect_multichannel(
    state: State<'_, AppState>,
    zip_path: String,
    model_names: Vec<String>,
) -> Result<DetectionResult, String> {
    let run_id = uuid::Uuid::new_v4().to_string();
    let output_dir = state.output_base.join(&run_id);
    std::fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;

    let extract_dir = output_dir.join("channels");
    std::fs::create_dir_all(&extract_dir).map_err(|e| e.to_string())?;

    let zip_file = std::fs::File::open(&zip_path).map_err(|e| e.to_string())?;
    let mut archive = zip::ZipArchive::new(zip_file).map_err(|e| e.to_string())?;
    archive
        .extract(&extract_dir)
        .map_err(|e| format!("ZIP extraction failed: {}", e))?;

    let model_paths: Vec<String> = model_names
        .iter()
        .map(|name| {
            state.model_dir
                .join("multi")
                .join(format!("{}.onnx", name))
                .to_string_lossy()
                .to_string()
        })
        .collect();

    let result = crate::inference::run_inference(
        &extract_dir.to_string_lossy(),
        output_dir.to_str().unwrap(),
        &state.python_bin,
        &state.python_dir,
        &model_paths,
        "multichannel",
    )?;

    let file_name = std::path::Path::new(&zip_path)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string());

    state.history.add(&result, &file_name);

    Ok(result)
}

#[tauri::command]
pub async fn list_models(
    state: State<'_, AppState>,
    mode: String,
) -> Result<Vec<ModelInfo>, String> {
    Ok(crate::inference::list_models(&state.model_dir, &mode))
}

#[tauri::command]
pub async fn detect_rgb_data(
    state: State<'_, AppState>,
    base64_data: String,
    model_names: Vec<String>,
    file_name: String,
) -> Result<DetectionResult, String> {
    let run_id = uuid::Uuid::new_v4().to_string();
    let output_dir = state.output_base.join(&run_id);
    std::fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;

    let image_path = output_dir.join("input.png");
    let image_path_str = image_path.to_string_lossy().to_string();
    crate::inference::save_base64_image(&base64_data, &image_path_str)?;

    let model_paths: Vec<String> = model_names
        .iter()
        .map(|name| {
            state.model_dir
                .join("rgb")
                .join(format!("{}.onnx", name))
                .to_string_lossy()
                .to_string()
        })
        .collect();

    let result = crate::inference::run_inference(
        &image_path_str,
        output_dir.to_str().unwrap(),
        &state.python_bin,
        &state.python_dir,
        &model_paths,
        "rgb",
    )?;

    state.history.add(&result, &file_name);

    Ok(result)
}

#[tauri::command]
pub async fn get_image_base64(path: String) -> Result<String, String> {
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    let bytes = std::fs::read(&path)
        .map_err(|e| format!("Failed to read image: {}", e))?;
    let ext = std::path::Path::new(&path)
        .extension()
        .map(|e| e.to_string_lossy().to_lowercase())
        .unwrap_or_else(|| "png".to_string());
    let mime = match ext.as_str() {
        "jpg" | "jpeg" => "image/jpeg",
        "bmp" => "image/bmp",
        _ => "image/png",
    };
    Ok(format!("data:{};base64,{}", mime, STANDARD.encode(&bytes)))
}

#[tauri::command]
pub async fn write_file_base64(path: String, base64_data: String) -> Result<(), String> {
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    let bytes = STANDARD.decode(&base64_data)
        .map_err(|e| format!("Failed to decode: {}", e))?;
    std::fs::write(&path, &bytes)
        .map_err(|e| format!("Failed to write file: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn get_history_list(
    state: State<'_, AppState>,
    query: String,
    filter_type: Option<u8>,
    sort_desc: bool,
    date_from: Option<String>,
    date_to: Option<String>,
) -> Result<Vec<HistoryItem>, String> {
    Ok(state.history.query(&query, filter_type, sort_desc, date_from, date_to))
}

#[tauri::command]
pub async fn get_history_detail(
    state: State<'_, AppState>,
    id: String,
) -> Result<Option<HistoryItem>, String> {
    Ok(state.history.get_by_id(&id))
}

#[tauri::command]
pub async fn delete_history(
    state: State<'_, AppState>,
    id: String,
) -> Result<bool, String> {
    Ok(state.history.delete(&id))
}
