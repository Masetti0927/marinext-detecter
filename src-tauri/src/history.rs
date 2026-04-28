use crate::inference::DetectionResult;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HistoryItem {
    pub id: String,
    pub file_name: String,
    pub date: String,
    pub original_path: String,
    pub mask_path: String,
    pub mode: String,
    pub primary_class: Option<u8>,
    pub stats: std::collections::HashMap<String, crate::inference::ClassStat>,
}

pub struct HistoryStore {
    data_dir: PathBuf,
}

impl HistoryStore {
    pub fn new(data_dir: PathBuf) -> Self {
        fs::create_dir_all(&data_dir).ok();
        Self { data_dir }
    }

    fn history_file(&self) -> PathBuf {
        self.data_dir.join("history.json")
    }

    pub fn load_all(&self) -> Vec<HistoryItem> {
        let path = self.history_file();
        if !path.exists() {
            return vec![];
        }
        fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    }

    fn save_all(&self, items: &[HistoryItem]) {
        let path = self.history_file();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).ok();
        }
        if let Ok(json) = serde_json::to_string_pretty(items) {
            fs::write(&path, json).ok();
        }
    }

    pub fn add(&self, result: &DetectionResult, file_name: &str) -> HistoryItem {
        let mut items = self.load_all();

        let primary_class = result
            .stats
            .values()
            .max_by(|a, b| a.percentage.partial_cmp(&b.percentage).unwrap())
            .map(|s| s.class_id);

        let item = HistoryItem {
            id: result.id.clone(),
            file_name: file_name.to_string(),
            date: result.timestamp.clone(),
            original_path: result.original_path.clone(),
            mask_path: result.mask_path.clone(),
            mode: result.mode.clone(),
            primary_class,
            stats: result.stats.clone(),
        };

        items.push(item.clone());
        self.save_all(&items);

        // Also save images to data dir for persistence
        let images_dir = self.data_dir.join("images");
        fs::create_dir_all(&images_dir).ok();
        let dest_original = images_dir.join(format!("{}_original", result.id));
        let dest_mask = images_dir.join(format!("{}_mask.png", result.id));
        fs::copy(&result.original_path, &dest_original).ok();
        fs::copy(&result.mask_path, &dest_mask).ok();

        item
    }

    pub fn delete(&self, id: &str) -> bool {
        let mut items = self.load_all();
        let len_before = items.len();
        items.retain(|item| item.id != id);
        if items.len() < len_before {
            self.save_all(&items);
            // Clean up images
            let images_dir = self.data_dir.join("images");
            let _ = fs::remove_file(images_dir.join(format!("{}_original", id)));
            let _ = fs::remove_file(images_dir.join(format!("{}_mask.png", id)));
            true
        } else {
            false
        }
    }

    pub fn get_by_id(&self, id: &str) -> Option<HistoryItem> {
        self.load_all().into_iter().find(|item| item.id == id)
    }

    pub fn query(
        &self,
        search: &str,
        filter_class: Option<u8>,
        sort_desc: bool,
        date_from: Option<String>,
        date_to: Option<String>,
    ) -> Vec<HistoryItem> {
        let mut items = self.load_all();

        if !search.is_empty() {
            let lower = search.to_lowercase();
            items.retain(|item| item.file_name.to_lowercase().contains(&lower));
        }

        if let Some(cls) = filter_class {
            items.retain(|item| item.primary_class == Some(cls));
        }

        if let Some(ref from) = date_from {
            items.retain(|item| item.date.as_str() >= from.as_str());
        }
        if let Some(ref to) = date_to {
            items.retain(|item| item.date.as_str() <= to.as_str());
        }

        items.sort_by(|a, b| {
            let cmp = a.date.cmp(&b.date);
            if sort_desc { cmp.reverse() } else { cmp }
        });

        items
    }
}
