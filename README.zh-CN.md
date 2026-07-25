# script2video

[English](README.md) | [简体中文](README.zh-CN.md)

一套本地优先的工具，可将直接粘贴的文本或结构化 YAML 脚本转换为旁白、定时字幕，
以及可在 CapCut 中继续编辑的素材包。

`script2video` 在你的电脑上完成语音生成和对齐。它可以逐场景渲染旁白、让
旁白时长适配现有视频，并生成标准 WAV、SRT 和 JSON 文件，无需修改 CapCut
项目文件。

> **状态：** 已可在 macOS 和 Windows 上本地使用。生成旁白不需要视频；只有在
> 需要带字幕和计时信息的 CapCut 素材包时才需要选择视频。

> **版本 1.0.3：** Windows 应用现在会在独立桌面窗口中打开 Studio，并可检查更新；
> 同时修复粘贴文本模式无法选择声音和打开输出文件夹失败的问题。空行分隔的段落会
> 自动成为场景。

> **版本 1.0.4 热修复：** 将 Kokoro 所需的语言注册表重新包含到 Windows
> 打包应用中，修复 v1.0.3 生成旁白时出现的
> `language_tags/data/json/index.json` 文件缺失错误。

## Studio 界面预览

![Script2Video Studio v1.0.3 工作区](docs/screenshots/studio-v1.0.3-overview.png)

工作区把脚本、旁白设置和生成状态集中在同一页面。默认可以直接粘贴文本，同时保留
YAML 模式，用于复用逐场景的高级设置。

![已识别两个场景并可开始生成的 Script2Video Studio](docs/screenshots/studio-v1.0.3-ready.png)

### v1.0.3 新功能

- 在 Windows 原生桌面窗口中打开 Studio，不再默认跳转浏览器标签页。
- 启动后自动检查 GitHub Releases，也可以点击 **Check for updates** 手动检查。
- 粘贴文本后可以正常选择所有兼容声音。
- 自动把空行分隔的段落转换为场景，并实时显示场景数和字数。
- 脚本和声音准备完成前，保持 **Generate Narration** 按钮不可用。
- 只有文件真正生成完成后才显示完成面板。
- 在 Windows、macOS 和 Linux 上可靠打开输出文件夹。
- 打包应用默认把结果保存到 `Documents/Script2Video Studio`。

## 选择工作流程

| 目标 | 是否需要视频 | 输出 |
| --- | --- | --- |
| 生成语音旁白 | 否 | `narration.wav`、各场景 WAV 和 `manifest.json` |
| 创建 CapCut 素材包 | 是 | 旁白、可编辑的 `captions.srt`、场景音频和计时信息 |

## 只需安装一次

安装不需要 Git。请下载
[最新项目 ZIP](https://github.com/saslifat-gif/script2video/archive/refs/heads/main.zip)，
解压后，在 `script2video-main` 文件夹中打开终端。

`script2video` 目前作为本地 Python 应用运行，需要 Python 3.11。只有选择视频时
才需要 FFmpeg。

首次安装真实语音功能时会包含 PyTorch、Transformers、tokenizers、spaCy 和
Kokoro 的语言工具。这是正常现象，可能需要几分钟。首次渲染会下载所选声音模型，
后续运行会复用本地缓存。

### macOS

安装 Python 和应用：

```bash
brew install python@3.11 espeak-ng
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[kokoro,alignment]"
```

如果要选择视频并创建 CapCut 素材包，请再运行 `brew install ffmpeg`。如果找不到
`brew` 命令，请先安装 [Homebrew](https://brew.sh/)。

AI 单词级对齐需要 Apple 芯片 Mac。Intel Mac 请改为安装 `.[kokoro]`，并使用
精确字幕块计时作为回退方案。

### Windows PowerShell

使用 Windows 程序包管理器安装 Python：

```powershell
winget install --exact --id Python.Python.3.11
```

安装完成后关闭 PowerShell，再在项目文件夹中重新打开。这样 Windows 才能识别
新安装的 `py` 命令。

在解压后的 `script2video-main` 文件夹中安装 Windows 兼容版本：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[kokoro]"
```

如果要选择视频并创建 CapCut 素材包，请再安装 FFmpeg：

```powershell
winget install --exact --id Gyan.FFmpeg
```

应用通常可以立即找到 Winget 安装的 FFmpeg。如果仍然找不到，请关闭并重新打开
应用一次。

每台电脑都必须创建独立的 `.venv`。不要把 Mac 的 `.venv` 复制或同步到 Windows；
`tokenizers`、NumPy 和音频库等编译依赖包含操作系统专用文件。项目已在 Git 中
忽略 `.venv/`，因此 Git 和项目 ZIP 只会传输源代码。

MLX Whisper 无法在 Windows 上运行。Studio 会自动禁用该功能，改用精确字幕块
计时。

Kokoro 通常会通过 Python 依赖提供音素支持。如果某个声音提示缺少 eSpeak
库，请从 [eSpeak NG 官方发布页](https://github.com/espeak-ng/espeak-ng/releases)
安装最新的 Windows MSI。

## 打开 Script2Video Studio

在 macOS 上运行：

```bash
.venv/bin/script2video companion
```

在 Windows PowerShell 中运行：

```powershell
.\.venv\Scripts\script2video.exe companion
```

打包后的 Windows 应用会在独立桌面窗口中打开 Script2Video Studio。命令行
`companion` 仍会使用默认浏览器作为轻量回退方式。两种方式都只通过
`127.0.0.1` 在本机提供页面，因此脚本、视频和生成的音频不会离开你的电脑。
使用命令行版本时请保持终端窗口开启，结束后在终端按 `Ctrl+C`。

## 快速开始

### 不选择视频，直接生成旁白

1. 打开 Script2Video Studio。
2. 保持选择 **Paste text（粘贴文本）**，输入需要朗读的内容。
3. 保持 **Video（视频）** 为空。
4. 选择语言、声音和输出文件夹。
5. 点击 **Generate Narration（生成旁白）**。
6. 完成后点击 **Open Output（打开输出）**。

每个段落会自动成为一个场景。输出文件夹包含 `script.txt`、`narration.wav`、
`manifest.json` 和各场景的独立 WAV 文件。此工作流程不需要 FFmpeg。需要复用
逐场景声音、语速和停顿设置时，可切换到 **YAML file（YAML 文件）**。

### 选择视频，创建 CapCut 素材包

按照相同步骤操作，但额外选择一个源视频。Studio 会切换为
**Generate CapCut Package（生成 CapCut 素材包）**，并增加 `captions.srt`、
时长适配和视频计时信息。随时点击 **Remove video（移除视频）** 即可返回纯旁白模式。

如果使用命令行，可通过以下命令验证脚本并渲染旁白：

```bash
script2video validate examples/demo.yaml
script2video voices --engine kokoro
script2video render examples/demo.yaml --output builds/demo
```

为现有视频生成时长适配的旁白和字幕：

```bash
script2video capcut examples/minecraft.yaml \
  --video /path/to/video.mp4 \
  --output builds/minecraft-capcut
```

结果会写入 `builds/minecraft-capcut/`，其中包含 `narration.wav`、
`captions.srt`、`manifest.json` 和各场景的 WAV 文件。

## 功能

- 使用 [Kokoro](https://github.com/hexgrad/kokoro) 在本地生成自然语音。
- 直接粘贴文本生成语音，无需编写 YAML。
- 自动把空行分隔的段落转换为场景。
- 在原生桌面窗口中运行打包后的界面。
- 在不影响离线使用的情况下检查 GitHub Releases 更新。
- 无需选择视频即可生成旁白。
- 分别渲染每个场景，并合成为一条标准化旁白。
- 根据原始脚本文本生成可编辑的 SRT 字幕。
- 在 Apple 芯片 Mac 上通过 MLX Whisper 对齐字幕和语音。
- 在安全语速范围内，让旁白时长适配视频。
- 生成包含音频、字幕和计时元数据的 CapCut 素材包。
- 提供确定性的假语音引擎，便于无模型快速开发和测试。
- 提供清晰、响应式的本地浏览器工作区，辅助 CapCut 工作流程。

## 工作原理

```text
原生桌面窗口或浏览器 Companion
                  |
             本地 Studio UI
                  |
          粘贴文本或 YAML 脚本
                  |
       +----------+----------+
       |                     |
     无视频                选择视频
       |                     |
  Kokoro 生成旁白       视频时长适配
       |                + 字幕语音对齐
       |                     |
 narration.wav       narration.wav + captions.srt
 各场景 WAV           各场景 WAV
 manifest.json       manifest.json
```

所有功能都通过仅绑定到 `127.0.0.1` 的本地服务运行。桌面启动器使用 pywebview
和 Windows Edge WebView2 嵌入界面；如果系统无法使用原生 WebView，应用会在
默认浏览器中打开同一个本地工作区。生成任务在后台运行，因此界面可以持续显示进度。

## 脚本格式

项目使用简洁的 YAML 文件保存设置和有序场景：

```yaml
title: Script2Video Demo
language: en-US
engine: kokoro
voice: af_heart

scenes:
  - id: intro
    text: Welcome. This script becomes locally generated narration.
    pause_after_ms: 500

  - id: explanation
    text: Each scene is rendered separately and recorded in the manifest.
    speed: 1.0
```

完整示例请查看 [`examples/demo.yaml`](examples/demo.yaml)。

## 创建 CapCut 素材包

生成与现有视频时长匹配的旁白和字幕：

```bash
script2video capcut examples/minecraft.yaml \
  --video /path/to/video.mp4 \
  --output builds/minecraft-capcut
```

输出目录结构如下：

```text
builds/minecraft-capcut/
├── narration.wav
├── captions.srt
├── manifest.json
└── scenes/
    └── 001-*.wav
```

默认情况下，该命令会：

1. 使用 `ffprobe` 测量视频时长。
2. 调整场景语速，使旁白适配视频时长。
3. 使用 MLX Whisper 将已知脚本文本与语音对齐。
4. 写出可编辑的音频、字幕和计时元数据。

为了保证旁白清晰易懂，适配器会拒绝 `0.50`–`2.00` 范围之外的语速。使用
`--no-fit` 可以保留脚本中的原始语速，使用 `--no-align` 可以改用精确字幕块
计时，使用 `--align-model base.en` 可以选择更大的英语对齐模型。

在 CapCut Desktop 中使用素材包：

1. 导入 `narration.wav`，并将其放在时间线起点。
2. 打开 **Captions → Add Captions**，以 UTF-8 格式导入 `captions.srt`。
3. 将字幕保留在时间线起点，然后应用你需要的字幕样式。

实现细节请查看 [`docs/m3-capcut.md`](docs/m3-capcut.md)。

## Studio 工作流程

响应式浏览器工作区可用于选择 YAML 脚本、源视频、输出文件夹和声音。它可以
显示脚本与视频信息、跟踪生成状态、打开输出文件夹并启动 CapCut。

Studio 通过标准文件导出，而不是直接修改 CapCut 项目，因为 CapCut 没有提供
公开的桌面插件 SDK。

## 语言和声音

支持的项目语言代码包括 `en-US`、`en-GB`、`es-ES`、`fr-FR`、`hi-IN`、
`it-IT`、`ja-JP`、`pt-BR` 和 `zh-CN`。所选声音必须支持项目语言。

列出 Kokoro 提供的所有声音：

```bash
script2video voices --engine kokoro
```

## 项目结构

```text
script2video/
├── src/script2video/
│   ├── desktop.py          # 原生应用窗口与浏览器回退
│   ├── webapp.py           # 本地 API、任务、更新检查和输出操作
│   ├── web_static/         # Studio HTML、CSS 和 JavaScript
│   ├── engines/            # Kokoro 与确定性假语音引擎
│   ├── pipeline.py         # 场景渲染与旁白合成
│   ├── alignment.py        # 可选的单词级语音对齐
│   ├── captions.py         # 易读的 SRT 字幕分段
│   ├── capcut.py           # 视频时长适配与 CapCut 素材包
│   └── cli.py              # validate、voices、render、capcut、companion
├── packaging/windows/      # PyInstaller 与 Inno Setup 配置
├── scripts/                # Windows 发布构建自动化
├── examples/               # 文本与 YAML 示例
├── docs/                   # 设计文档、打包说明和界面截图
└── tests/                  # 单元测试与回归测试
```

界面只与本地 API 通信。渲染管线不依赖桌面外壳，因此 Studio 和命令行都可以使用
同一套旁白与字幕功能。

## 开发

只有希望修改源代码的贡献者才需要 Git。克隆仓库并以可编辑模式安装：

```bash
git clone https://github.com/saslifat-gif/script2video.git
cd script2video
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,kokoro,alignment]"
```

在 Windows 上请使用 `.\.venv\Scripts\Activate.ps1` 激活环境，并从 extras 中
移除 `alignment`。

运行完整测试：

```bash
python -m pytest
```

如需在不下载语音模型的情况下快速测试，可将脚本中的引擎覆盖为确定性的假引擎：

```bash
script2video render examples/demo.yaml \
  --engine fake \
  --voice test_narrator \
  --output builds/demo-fake
```

假引擎会写入包含短测试音的有效 WAV 文件，因此无需托管 API 或模型下载，也可
进行端到端测试。

## 文档

- [第一阶段设计](docs/stage-1-design.md)
- [CapCut 素材包设计](docs/m3-capcut.md)
- [Windows 应用打包](docs/windows-packaging.md)

## 许可证

本项目按 [`LICENSE`](LICENSE) 中的条款授权。
