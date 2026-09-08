# script2video

[English](README.md) | [简体中文](README.zh-CN.md)

将粘贴的文案或 YAML 脚本转换为本地 Kokoro 旁白、带时间轴的字幕，以及可导入
CapCut 的文件。支持 **Windows 桌面应用**和 **Docker 浏览器应用**。

![Script2Video Studio](docs/screenshots/studio-v1.0.12-overview.png)

## Docker 安装

安装并启动 Docker Engine（含 Compose）或 Docker Desktop。在仓库目录运行：

```bash
mkdir -p data/input data/output
docker compose up --build -d
```

打开 **http://127.0.0.1:8765**。首次构建需要下载 Python 和语音依赖；首次生成
还需要下载 Kokoro 模型。模型保存在持久化的 `model-cache` 卷中。镜像使用 CPU
推理，并以非 root 用户运行。

- 直接粘贴文案，选择语言和声音即可生成旁白与字幕。
- 将 YAML 或视频放入电脑上的 `data/input`，在页面输入容器内路径，例如
  `/data/input/script.yaml` 或 `/data/input/video.mp4`。
- 输出目录保持 `/data/output`；每次生成的文件出现在电脑的 `data/output`
  下独立的日期文件夹中。
- 在电脑上打开 CapCut，导入生成的 WAV 和 SRT。

输入目录为只读挂载。Docker 模式隐藏原生文件选择器、“打开输出目录”和
“打开 CapCut”按钮。服务仅映射到本机地址，并保留来源检查和会话令牌保护。
请保持主机和容器两侧端口都为 8765；当前配置不提供远程网站访问。
如果已有 Studio 占用该端口，请先停止旧实例。

```bash
docker compose logs -f studio
docker compose down
docker compose up --build -d
```

`docker compose down` 不删除模型缓存和输入、输出文件。只有确定要删除模型
缓存时才添加 `--volumes`。Linux 上请确保容器 UID 1000 对输出目录有写权限；
若当前账号 UID 不同，请调整输出目录所有者，不要开放所有用户写权限。

## Windows 安装

从 [GitHub Releases](https://github.com/saslifat-gif/script2video/releases)
下载 Windows x64 安装程序。应用在独立窗口中打开 Studio。默认输出目录为
`Documents/Script2Video Studio`，每次生成使用独立文件夹。

从源码运行需要 Python 3.11：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[kokoro]"
.\.venv\Scripts\script2video.exe companion
```

使用视频时安装 FFmpeg：

```powershell
winget install --exact --id Gyan.FFmpeg
```

如果提示缺少 eSpeak，请从 [eSpeak NG 官方发布页](https://github.com/espeak-ng/espeak-ng/releases)
安装。不要直接打开 `web_static/index.html`，页面需要通过 Studio 本地服务运行。

## 字幕与视频时间轴

可按句子、段落、换行或全文划分场景。短字幕块分别生成音频，字幕使用实际
音频段时长，并排除首尾的近静音，保留少量余量以保护轻声发音。不会剪掉音频、
改变内部停顿或移动后续场景。

Windows 和 Docker 均使用实测字幕时间，不需要额外的对齐模型。Python 通用
对齐接口保留给集成使用；若外部对齐结果不可靠，会回退到实测时间并记录提醒。

选择视频后，系统在 0.50–2.00 倍语速范围内匹配视频时长。三次尝试后仍无法
匹配时，会保存文件并显示提醒，`manifest.json` 也记录该提醒。
已有输出需要重新生成，才能应用时间轴修复。

将 `narration.wav` 与 `captions.srt` 导入 CapCut，两者都从时间轴零点开始。
Studio 输出标准文件，不直接修改 CapCut 工程，也不导出完整成片。

## 开发

在 Python 3.11 环境安装 `.[dev,kokoro]` 后运行：

```bash
python -m pytest
node --test tests/studio-ui.test.cjs
```

测试使用无需下载模型的模拟语音引擎。语言、YAML、命令行说明请参阅
[英文文档](README.md)。项目授权参阅 [LICENSE](LICENSE)。
