# Marine Detecter

基于深度学习的海洋目标检测桌面应用，支持 RGB 图像和多通道（11波段）多光谱影像的语义分割，共15类海洋地物识别。

## 功能

- **图像检测** — RGB 图像裁剪、旋转、缩放后推理，或导入多通道 ZIP 压缩包
- **对比可视化** — 原图与 mask 叠加显示，支持缩放拖拽、类别筛选、透明度/阈值调节
- **历史记录** — 本地持久化，支持按类别/日期搜索过滤
- **统计图表** — 各类别像素占比饼图、多模型预测对比
- **报告导出** — 一键生成 XLSX 检测报告
- **中英文切换** — 界面完整国际化

## 技术栈

| 层 | 技术 |
|---|---|
| 桌面框架 | Tauri v2 (Rust) |
| 前端 | Vue 3 + Vite + Pinia + Vue Router |
| 图表 | ECharts |
| 推理引擎 | ONNX Runtime (Python) |
| 多光谱处理 | rasterio / PIL |
| 国际化 | vue-i18n |

## 运行

```bash
# 安装前端依赖
npm install

# 开发模式
npm run tauri dev

# 构建
npm run tauri build
```

## 项目结构

```
src/                         # Vue 前端
├── views/                   # 页面组件
│   ├── DetectPage.vue       # 检测页（RGB裁剪 / 多通道ZIP）
│   ├── ContrastPage.vue     # 原图与mask对比
│   ├── HistoryPage.vue      # 历史记录
│   ├── ChartsPage.vue       # 统计图表
│   └── ReportPage.vue       # 报告导出
├── stores/                  # Pinia 状态管理
├── composables/             # 可组合逻辑
├── i18n/                    # 中英文语言包
└── App.vue                  # 主布局（侧边栏 + 页脚状态栏）

src-tauri/                   # Rust 后端
├── src/
│   ├── lib.rs               # 应用入口，Tauri setup
│   ├── commands.rs          # Tauri 命令（检测、历史、文件操作）
│   ├── inference.rs         # ONNX 推理调用（Python子进程）
│   └── history.rs           # 历史记录持久化（JSON）
└── python/
    └── main.py              # ONNX 推理脚本（RGB / 多通道）
```

## 可移植设计

所有运行时数据（检测输出、历史记录、图片缓存）存储在可执行文件同级 `data/` 目录下，不依赖用户目录或系统路径，U盘拷走即用。
