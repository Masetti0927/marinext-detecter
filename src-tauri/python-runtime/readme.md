# 便携式 Python 环境配置指南  
  
本文档介绍如何在项目中集成独立的 Python 运行时，以实现无需系统全局安装 Python 即可运行推理任务。  
  
## 1. 下载便携式 Python 运行时  
  
访问以下网址获取最新的 Python 构建：  
[python-build-standalone Releases](https://github.com/astral-sh/python-build-standalone/releases)  
  
**选择建议：**  
找到最新的发布版本（Tag 类似 `20250317`），并根据系统下载对应的文件。例如：  
`cpython-3.11.14+20250317-x86_64-unknown-linux-gnu-install_only.tar.gz`  
  
**关键筛选条件：**  
* **平台：** `x86_64-unknown-linux-gnu`（适用于 Linux 64位系统）  
* **版本：** 推荐 `install_only` 类型（仅含标准库，体积更小，适合分发）  
  
---  
  
## 2. 解压与目录初始化  
  
在项目路径下执行以下命令，将 Python 环境放置在 `src-tauri` 目录中：  
  
```bash  
# 进入目标目录  
cd src-tauri  
  
# 解压压缩包  
tar xzf ~/Downloads/cpython-3.11.*-x86_64-unknown-linux-gnu-install_only.tar.gz  
  
# 规范化目录命名  
mv python python-runtime 2>/dev/null || true  
 ``` 
预期目录结构：  
  
src-tauri/python-runtime/  
├── bin/  
│   └── python3          # 独立 Python 执行程序  
├── lib/  
│   └── python3.11/  
│       ├── ...  
│       └── site-packages/   # 第三方包存放处  
└── ...  
 
## 3. 安装项目依赖  
使用该便携式环境自带的工具安装所需的 Python 库：  
```bash
# 升级并启用 pip
./python-runtime/bin/python3 -m ensurepip --upgrade  
# 安装推理相关依赖（会自动安装进 site-packages）  
./python-runtime/bin/python3 -m pip install onnxruntime numpy Pillow
```  
**运行环境验证：** 执行以下命令，若输出 `OK` 则表示环境就绪：

```bash
./python-runtime/bin/python3 -c "import onnxruntime, numpy, PIL; print('OK')"
```
## 4. 放置模型文件

确保模型文件放置在项目指定的 `models` 目录下：

```Bash
# 创建模型目录（如不存在）
mkdir -p src-tauri/models/

# 拷贝模型
cp /path/to/your/model/marinext_rgb_ema.onnx src-tauri/models/
```
