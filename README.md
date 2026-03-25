# 🧠 AI 学术伴读引擎 (AI Academic Reader)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)
![Release](https://img.shields.io/badge/Release-v1.0.0-orange.svg)

**一款专为硬核学术文献（论文、计算机教材）设计的桌面端 AI 沉浸式伴读工具。** 传统翻译软件在面对 PDF 论文中的复杂数学公式、多栏排版和代码块时往往会变成“乱码制造机”。本项目通过高容错的局部屏幕 OCR 捕获技术，结合大语言模型（DeepSeek / Qwen / Gemini），并在独立的极速 Web 渲染引擎中，为你提供**毫秒级排版、公式完美还原、无缝衔接**的流式翻译与上下文深度问答体验。

---

## ✨ 核心特性 (Key Features)

### 🎯 1. 视口防抖与智能滚动追踪
- **高容错“秒级防抖”监控**：彻底告别传统 OCR 划词软件频繁的“闪烁重载”痛点。独创「连续稳定帧检测」与基于 `difflib` 的文本相似度（>90%）过滤算法，精准免疫鼠标划过、光标闪烁等视觉噪点。
- **无痕内容拼接**：引入 `Rolling Window`（滑动窗口）淘汰机制。当向下滚动阅读时，新翻译的内容会像打字机一样自然追加，而视野外超过 3 个区块的旧内容会被后台静默销毁，保障极低的内存占用与纯净的阅读视野。

### ⚡ 2. 所见即所得的极速渲染 (WYSIWYG)
- **B/S 混合架构**：摒弃性能羸弱的 Python 原生 GUI 文本框，内置本地 WebSocket 服务驱动 Web 渲染引擎。
- **动态排版引擎**：结合 `KaTeX`（极速同步公式渲染）与 `Highlight.js`（代码语法高亮），在 AI 流式输出的瞬间，同步完成复杂的 LaTeX 矩阵公式排版，彻底消除“先乱码后成型”的视觉跳动感。

### 🛡️ 3. 底层网络强力突防
- **代理与证书免疫**：针对 Mac 环境下常见的 Anaconda SSL 证书丢失、VPN 代理路由冲突导致 LLM API 报错的痛点，弃用脆弱的官方高封装 SDK。
- **手搓底层请求**：基于原生 `requests` 手写 HTTP 流式协议（SSE），强制剥离系统环境变量中的代理挂载，实施分级超时控制（翻译 20s / 问答 120s），确保 99.9% 的连接成功率。

### 💬 4. 具备“海马体”的问答抽屉
- **局部上下文记忆**：在内存中构建基于 `deque` 的双端队列，自动维护用户最近 5 屏的阅读上下文。
- **侧边栏悬浮问答**：阅读中遇到不懂的推导过程，随时在控制台提问。网页右侧滑出独立问答抽屉，支持横向滚动的响应式 Markdown 表格，解答内容永久留存。

---

## 🛠️ 技术栈 (Tech Stack)

- **核心后端**：`Python 3.12`, `CustomTkinter` (UI), `Websockets` (全双工通信), `Requests`
- **图像与 OCR**：`Tesseract-OCR` (光学字符识别), `mss` (极速内存截屏), `Pillow` (图像差分计算)
- **前端渲染引擎**：`HTML5`, `Tailwind CSS`, `Marked.js`, `KaTeX`, `Highlight.js`
- **大模型 API 支持**：`DeepSeek-Chat` / `DeepSeek-Reasoner (R1)` / `Qwen-Max` / `Gemini 1.5 Pro`


## 🚀 快速开始 (Quick Start)

### 1. 准备 Tesseract 引擎
本项目依赖底层的 Tesseract OCR 引擎进行文字提取，请先在系统中安装它：

- **macOS** (推荐使用 Homebrew):
  ```bash
  brew install tesseract
  ```

- **Windows**:
  请前往 [UB-Mannheim Tesseract](https://www.google.com/search?q=https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包，并将安装路径（如 `C:\Program Files\Tesseract-OCR`）添加到系统的环境变量 `PATH` 中。
  *(注：Windows 用户可能需要修改 `main.py` 中的 `tesseract_cmd` 路径指向你的 `tesseract.exe`)*

### 2\. 克隆项目与安装依赖

建议使用 `conda` 或 `venv` 创建独立的虚拟环境：

```bash
git clone [https://github.com/mabcex/ai-academic-reader.git](https://github.com/mabcex/ai-academic-reader.git)
cd ai-academic-reader
pip install -r requirements.txt
```

### 3\. 运行程序

```bash
python main.py
```

### 4\. 使用指南

1.  **配置 API**：程序启动后，点击 **[⚙️ 设置 API]**，填入你的 DeepSeek 或 Qwen 的 API Key。
2.  **框选监控**：点击 **[⛶ 框选区域]**，用红色十字准星框住你的 PDF 阅读器内容区域。
3.  **开启伴读**：框选完成后，系统会自动在默认浏览器弹出【AI 学术伴读渲染引擎】网页。
4.  **尽情阅读**：在左侧正常向下翻阅文献，右侧网页会自动、静默、极速地生成完美的翻译与排版。
5.  **深度提问**：在 Python 控制台底部输入问题并回车，网页右侧会滑出问答抽屉提供详细解答。

<!-- end list -->

