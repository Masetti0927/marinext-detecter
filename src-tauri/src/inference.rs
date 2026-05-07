use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ClassStat {
    pub class_id: u8,
    pub pixel_count: u64,
    pub percentage: f64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DetectionResult {
    pub id: String,
    pub original_path: String,
    pub mask_path: String,
    pub original_base64: String,
    pub mask_base64: String,
    pub stats: HashMap<String, ClassStat>,
    pub total_pixels: u64,
    pub timestamp: String,
    pub mode: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelInfo {
    pub name: String,
    pub path: String,
}

#[derive(Debug, Deserialize)]
struct PythonOutput {
    mask_path: String,
    stats: HashMap<String, ClassStat>,
    total_pixels: u64,
    error: Option<String>,
}

pub fn list_models(model_dir: &PathBuf, mode: &str) -> Vec<ModelInfo> {
    let dir = model_dir.join(mode);
    let mut models = Vec::new();

    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map_or(false, |ext| ext == "onnx") {
                models.push(ModelInfo {
                    name: path.file_stem()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_default(),
                    path: path.to_string_lossy().to_string(),
                });
            }
        }
    }

    models.sort_by(|a, b| a.name.cmp(&b.name));
    models
}

pub fn run_inference(
    input_path: &str,
    output_dir: &str,
    python_bin: &PathBuf,
    python_dir: &PathBuf,
    model_paths: &[String],
    mode: &str,
    use_tta:bool,
) -> Result<DetectionResult, String> {
    let script_path = python_dir.join("main.py");

    if !script_path.exists() {
        return Err(format!("Python script not found at {:?}", script_path));
    }

    if model_paths.is_empty() {
        return Err("No models selected".to_string());
    }

    for mp in model_paths {
        if !std::path::Path::new(mp).exists() {
            return Err(format!("Model not found: {}", mp));
        }
    }

    let python = if python_bin.exists() {
        python_bin.as_os_str()
    } else {
        #[cfg(target_os = "windows")]
        { std::ffi::OsStr::new("python") }
        #[cfg(not(target_os = "windows"))]
        { std::ffi::OsStr::new("python3") }
    };

    let mut cmd = Command::new(python);
    cmd.arg(&script_path)
        .arg("--input").arg(input_path)
        .arg("--output").arg(output_dir)
        .arg("--mode").arg(mode)
        .arg("--models");

    for mp in model_paths {
        cmd.arg(mp);
    }

    if use_tta {
        cmd.arg("--use-tta");
    }
    // Hide console window on Windows
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let output = cmd.output()
        .map_err(|e| format!("Failed to spawn Python: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python process failed: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let py_output: PythonOutput = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Failed to parse Python output: {}\nstdout: {}", e, stdout))?;

    if let Some(err) = py_output.error {
        return Err(err);
    }

    // Read images as base64 for frontend display
    let original_base64 = if mode == "multichannel" {
        String::new()
    } else {
        image_to_base64(input_path)?
    };
    let mask_base64 = image_to_base64(&py_output.mask_path)?;

    let id = uuid::Uuid::new_v4().to_string();
    let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

    Ok(DetectionResult {
        id,
        original_path: input_path.to_string(),
        mask_path: py_output.mask_path,
        original_base64,
        mask_base64,
        stats: py_output.stats,
        total_pixels: py_output.total_pixels,
        timestamp,
        mode: mode.to_string(),
    })
}

pub fn save_base64_image(data_url: &str, output_path: &str) -> Result<(), String> {
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    // Strip data URL prefix: "data:image/png;base64,"
    let base64_data = if let Some(comma_pos) = data_url.find(',') {
        &data_url[comma_pos + 1..]
    } else {
        data_url
    };
    let bytes = STANDARD.decode(base64_data)
        .map_err(|e| format!("Failed to decode base64: {}", e))?;
    std::fs::write(output_path, &bytes)
        .map_err(|e| format!("Failed to write image file: {}", e))?;
    Ok(())
}

pub fn image_to_base64(path: &str) -> Result<String, String> {
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    let bytes = std::fs::read(path)
        .map_err(|e| format!("Failed to read image for base64: {}", e))?;
    let ext = std::path::Path::new(path)
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
