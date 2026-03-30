# 🧠 AI 学术伴读引擎 (AI Academic Reader)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)
![Release](https://img.shields.io/badge/Release-v1.0.0-orange.svg)

**嗨！这是一个我自己折腾出来的桌面端 AI 伴读小工具。**

**一款专为硬核学术文献（论文、计算机教材）设计的桌面端 AI 沉浸式伴读工具。** 传统翻译软件在面对 PDF 论文中的复杂数学公式、多栏排版和代码块时往往会变成“乱码制造机”。本项目通过高容错的局部屏幕 OCR 捕获技术，结合大语言模型（DeepSeek / Qwen / Gemini），并在独立的极速 Web 渲染引擎中，为你提供**毫秒级排版、公式完美还原、无缝衔接**的流式翻译与上下文深度问答体验。

---

## ✨ 核心特性 (Key Features)

### 🎯 1. 视口防抖与智能滚动追踪
- **“二值化”光照免疫与秒级防抖**：引入强制灰度二值化（Binarization）图像处理算法，**完美过滤 macOS 原彩显示（True Tone）和自动亮度变化带来的全局像素噪点**。结合 `difflib` 文本相似度过滤，只有真正的文字结构变化才会触发翻译，彻底告别传统划词软件的“闪烁重载”痛点。
- **无痕内容拼接**：引入 `Rolling Window`（滑动窗口）淘汰机制。当向下滚动阅读时，新翻译的内容会像打字机一样自然追加，而视野外超过 3 个区块的旧内容会被后台静默销毁，保障极低的内存占用与纯净的阅读视野。

### ⚡ 2. 所见即所得的极速渲染 (WYSIWYG)
- **B/S 混合架构**：摒弃性能羸弱的 Python 原生 GUI 文本框，内置本地 WebSocket 服务驱动 Web 渲染引擎。
- **动态排版引擎**：结合 `KaTeX`（极速同步公式渲染）与 `Highlight.js`（代码语法高亮），在 AI 流式输出的瞬间，同步完成复杂的 LaTeX 矩阵公式排版，彻底消除“先乱码后成型”的视觉跳动感。

### 🛡️ 3. 底层网络突防与“并发斩杀”
- **代理与证书免疫**：针对 Mac 环境下常见的 SSL 证书丢失、VPN 代理路由冲突导致 LLM API 报错的痛点，弃用脆弱的官方高封装 SDK，手搓原生 `requests` 流式协议绕过系统级代理干扰。
- **毫秒级任务抢占与 TCP 阻断**：独创 `Task ID` 抢占机制。在快速连续翻页时，底层会直接抛出中断异常并**暴力掐断旧的 HTTP TCP 连接**。不仅实现零延迟的新页面渲染，更极致节省大模型 Token 消耗，绝不让无效翻译阻塞线程！

### 💬 4. 具备“海马体”的问答抽屉
- **超长局部上下文记忆**：在内存中构建基于 `deque` 的双端队列，脑容量扩充至记录用户最近 **40 屏** 的阅读上下文（告别大海捞针，完美覆盖整章核心内容）。
- **“费曼技巧”导师设定**：深度调优的 Prompt 架构。侧边栏悬浮提问时，AI 会强行采用“费曼技巧 + 硬核学术黑话”的逻辑链条（核心结论 -> 原理通俗解析 -> 实例推导）为你解答推导过程，拒绝废话，直奔主题。

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



## 🤝 碎碎念 

做这个小工具最初只是为了解决自己看英文论文的痛点，顺便练练手。

因为个人技术水平还在不断升级中，目前的版本肯定还有写得比较“菜”或者粗糙的地方 😅，也可能藏着一些我还没踩到的 Bug 🐛。

**我有空也会不断更新和完善它的哈哈 🚀**

如果大家在用的过程中遇到了什么问题，或者有什么好玩的改进想法，随时欢迎在 Issue 告诉我交流！要是路过的大佬愿意顺手提个 PR 帮我修修 Bug、改改错，那我简直感激不尽！

