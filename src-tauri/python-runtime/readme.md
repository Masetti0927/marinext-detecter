1. 下载便携式 Python 运行时
打开浏览器访问这个网址：

https://github.com/astral-sh/python-build-standalone/releases

找到 最新发布（tag 类似 20250317），在 Assets 里找到这个文件下载：

cpython-3.11.14+20250317-x86_64-unknown-linux-gnu-install_only.tar.gz

文件名里的版本号和日期可能不同，关键是：

带 x86_64-unknown-linux-gnu（Linux 64位）
带 install_only（只含标准库，不含 pip，体积更小）
2. 解压到项目目录
cd marine_detecter/src-tauri

# 解压
tar xzf ~/Downloads/cpython-3.11.*-x86_64-unknown-linux-gnu-install_only.tar.gz

# 重命名为 python-runtime（如果解压出来是 python/ 目录）
mv python python-runtime 2>/dev/null || true

解压后的目录结构应该是：

src-tauri/python-runtime/
├── bin/
│   └── python3          # 这就是嵌入式 Python
├── lib/
│   └── python3.11/
│       ├── ...
│       └── site-packages/   # 第三方包装在这里
└── ...

3. 安装 Python 依赖
# 用嵌入式 Python 自带的 ensurepip 安装 pip
./python-runtime/bin/python3 -m ensurepip --upgrade

# 安装依赖（会自动装进 site-packages）
./python-runtime/bin/python3 -m pip install onnxruntime numpy Pillow

验证一下是否能正常 import：

./python-runtime/bin/python3 -c "import onnxruntime, numpy, PIL; print('OK')"

4. 放置模型文件
cp /你的模型路径/marinext_rgb_ema_upscale.onnx \
   /home/masetti/Desktop/my_tauri/marine_detecter/src-tauri/models/