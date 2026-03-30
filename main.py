import customtkinter as ctk
import tkinter as tk
import threading
import time
import mss
import pytesseract
from PIL import Image, ImageChops, ImageStat
import config
from engines import CloudLLM
import psutil
from pynput import keyboard
from collections import deque
import asyncio
import websockets
import json
import webbrowser
import os
import difflib
import urllib.parse

pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ================= HTML 引擎内置生成 =================
HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI 学术伴读渲染引擎</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; overflow: hidden; }
        .thinking-box { color: #8b949e; border-left: 4px solid #30363d; padding-left: 10px; margin-bottom: 20px; font-size: 0.95em; white-space: pre-wrap; }
        .content-box { font-size: 1.1em; line-height: 1.6; }

        /* 【核心修复】：为 Markdown 元素重新注入样式，对抗 Tailwind 的强行重置 */
        .content-box table { width: 100%; border-collapse: collapse; margin: 1em 0; display: block; overflow-x: auto; white-space: nowrap; }
        .content-box th, .content-box td { border: 1px solid #30363d; padding: 8px 16px; text-align: left; }
        .content-box th { background-color: #161b22; font-weight: 600; color: #58a6ff; }
        .content-box tr:nth-child(even) { background-color: rgba(255,255,255,0.02); }
        .content-box ul { list-style-type: disc; padding-left: 2rem; margin-bottom: 1rem; }
        .content-box ol { list-style-type: decimal; padding-left: 2rem; margin-bottom: 1rem; }
        .content-box blockquote { border-left: 4px solid #3b82f6; padding-left: 1rem; margin: 1rem 0; color: #8b949e; background: rgba(59, 130, 246, 0.1); py-2; }
        .content-box strong { color: #e6edf3; font-weight: 600; }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
    </style>
</head>
<body class="p-8 max-w-4xl mx-auto h-screen flex flex-col relative">

    <div class="flex justify-between items-center border-b border-gray-700 pb-4 mb-6 shrink-0">
        <h1 class="text-2xl font-bold text-blue-400">🧠 AI 学术伴读引擎</h1>
        <span id="status" class="text-red-400 font-bold text-sm">● 未连接</span>
    </div>

    <div id="display-area" class="flex-1 overflow-y-auto pb-32 scroll-smooth">
        <div id="thinking-box" class="thinking-box hidden"></div>
        <div id="main-content" class="content-box text-gray-200">
            <div class="text-center text-gray-500 mt-20">等待屏幕监控启动...</div>
        </div>
    </div>

    <button id="qa-toggle" class="fixed bottom-8 right-8 bg-blue-600 hover:bg-blue-500 text-white rounded-full w-14 h-14 shadow-xl z-40 flex items-center justify-center transition-all cursor-pointer">
        <span class="text-2xl">💬</span>
    </button>

    <div id="qa-panel" class="fixed top-0 right-0 h-full w-96 bg-[#0d1117] border-l border-gray-700 shadow-2xl transform translate-x-full transition-transform duration-300 z-50 flex flex-col">
        <div class="p-4 border-b border-gray-700 flex justify-between items-center bg-[#161b22] shrink-0">
            <h2 class="text-lg font-bold text-blue-400">💬 深度问答历史</h2>
            <button id="qa-close" class="text-gray-400 hover:text-white text-xl px-2 cursor-pointer">✖</button>
        </div>
        <div id="qa-content" class="flex-1 overflow-y-auto p-4 pb-10">
            <div id="qa-empty" class="text-gray-500 text-sm text-center mt-10">还没有提问过哦，在控制台发送问题即可~</div>
        </div>
    </div>

    <script>
        let ws;
        let rawThinking = "";
        let rawContent = "";

        const statusEl = document.getElementById('status');
        const displayArea = document.getElementById('display-area');
        const mainContent = document.getElementById('main-content');
        const thinkingBox = document.getElementById('thinking-box');

        const qaToggle = document.getElementById('qa-toggle');
        const qaPanel = document.getElementById('qa-panel');
        const qaClose = document.getElementById('qa-close');
        const qaContent = document.getElementById('qa-content');
        const qaEmpty = document.getElementById('qa-empty');

        qaToggle.onclick = () => qaPanel.classList.remove('translate-x-full');
        qaClose.onclick = () => qaPanel.classList.add('translate-x-full');

        function renderContent(element, rawText) {
            element.innerHTML = marked.parse(rawText);
            element.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
            renderMathInElement(element, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\\\(', right: '\\\\)', display: false},
                    {left: '\\\\[', right: '\\\\]', display: true}
                ],
                throwOnError: false
            });
        }

        function connect() {
            ws = new WebSocket("ws://127.0.0.1:8766");
            ws.onopen = () => {
                statusEl.textContent = "● 已连接 (引擎就绪)";
                statusEl.className = "text-green-400 font-bold text-sm";
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === "clear") {
                    rawThinking = ""; 
                    rawContent = "";
                    thinkingBox.classList.add("hidden");
                    thinkingBox.textContent = "";
                    mainContent.innerHTML = "<span class='text-gray-500'>[读取新屏幕并翻译中...]</span>";
                } 
                else if (data.type === "stream") {
                    if (data.is_thinking) {
                        rawThinking += data.content;
                        thinkingBox.classList.remove("hidden");
                        thinkingBox.textContent = rawThinking;
                    } else {
                        rawContent += data.content;
                        renderContent(mainContent, rawContent);
                    }
                    displayArea.scrollTop = displayArea.scrollHeight;
                } 
                else if (data.type === "done") {
                    renderContent(mainContent, rawContent);
                    displayArea.scrollTop = displayArea.scrollHeight;
                } 
                else if (data.type === "question") {
                    if(qaEmpty) qaEmpty.style.display = 'none';
                    qaPanel.classList.remove('translate-x-full'); 

                    const qDiv = document.createElement("div");
                    qDiv.className = "my-4 p-3 bg-blue-900/30 border-l-4 border-blue-500 rounded text-blue-100 text-sm";
                    qDiv.innerHTML = `<strong>👤 你：</strong> ${data.content}`;
                    qaContent.appendChild(qDiv);

                    const loadingDiv = document.createElement("div");
                    loadingDiv.id = "qa-loading";
                    loadingDiv.className = "my-4 p-3 bg-gray-800 rounded content-box border border-gray-700 text-sm text-gray-400 animate-pulse";
                    loadingDiv.innerHTML = `⏳ <strong>AI 正在深度思考并查阅上下文...</strong>`;
                    qaContent.appendChild(loadingDiv);

                    qaContent.scrollTop = qaContent.scrollHeight;
                } 
                else if (data.type === "answer_done") {
                    const loader = document.getElementById("qa-loading");
                    if (loader) loader.remove();

                    const aDiv = document.createElement("div");
                    aDiv.className = "my-4 p-3 bg-gray-800 rounded content-box border border-gray-700 text-sm";
                    renderContent(aDiv, `<strong>🤖 解答：</strong><br><br>` + data.content);
                    qaContent.appendChild(aDiv);
                    qaContent.scrollTop = qaContent.scrollHeight;
                }
            };
            ws.onclose = () => {
                statusEl.textContent = "● 断开连接...";
                statusEl.className = "text-red-400 font-bold text-sm";
                setTimeout(connect, 2000);
            };
        }
        connect();
    </script>
</body>
</html>
"""


def generate_and_open_html():
    file_path = os.path.abspath("auto_reader.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    safe_path = urllib.parse.quote(file_path)
    try:
        webbrowser.open('file://' + safe_path)
        print("[系统] 🟢 已在默认浏览器中打开渲染引擎")
    except Exception as e:
        pass


connected_clients = set()
ws_loop = None


async def ws_handler(websocket):
    connected_clients.add(websocket)
    try:
        async for msg in websocket: pass
    except:
        pass
    finally:
        connected_clients.remove(websocket)


async def main_ws():
    global ws_loop
    ws_loop = asyncio.get_running_loop()
    try:
        async with websockets.serve(ws_handler, "127.0.0.1", 8766):
            await asyncio.Future()
    except Exception as e:
        print(f"\n[致命错误] 🔴 WebSocket 启动失败: {e}")


def start_ws_server():
    asyncio.run(main_ws())


def broadcast_to_web(msg_type, content, is_thinking=False):
    try:
        if not ws_loop or not ws_loop.is_running(): return
        data = json.dumps({"type": msg_type, "content": content, "is_thinking": is_thinking})
        for ws in list(connected_clients):
            asyncio.run_coroutine_threadsafe(ws.send(data), ws_loop)
    except:
        pass


threading.Thread(target=start_ws_server, daemon=True).start()


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, current_config, save_callback):
        super().__init__(parent)
        self.title("配置 API")
        self.geometry("400x380")
        self.attributes("-topmost", True)
        self.save_callback = save_callback
        self.model_var = ctk.StringVar(value=current_config["active_model"])
        ctk.CTkOptionMenu(self, values=["DeepSeek", "Qwen", "Gemini"], variable=self.model_var).pack(pady=(20, 5))
        self.ds_entry = self.create_entry("DeepSeek API Key:", current_config["api_keys"].get("DeepSeek", ""))
        self.qwen_entry = self.create_entry("Qwen API Key:", current_config["api_keys"].get("Qwen", ""))
        self.gemini_entry = self.create_entry("Gemini API Key:", current_config["api_keys"].get("Gemini", ""))
        ctk.CTkButton(self, text="保存配置", command=self.save_settings).pack(pady=20)

    def create_entry(self, label, val):
        ctk.CTkLabel(self, text=label).pack(pady=(10, 0))
        entry = ctk.CTkEntry(self, width=250, show="*")
        entry.insert(0, val)
        entry.pack(pady=5)
        return entry

    def save_settings(self):
        self.save_callback({
            "active_model": self.model_var.get(),
            "api_keys": {"DeepSeek": self.ds_entry.get(), "Qwen": self.qwen_entry.get(),
                         "Gemini": self.gemini_entry.get()}
        })
        self.destroy()


class ScreenSelector(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.attributes("-alpha", 0.3)
        self.overrideredirect(True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.start_x = self.start_y = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red',
                                                 width=3)

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        ex, ey = event.x, event.y
        self.destroy()
        x1, x2 = min(self.start_x, ex), max(self.start_x, ex)
        y1, y2 = min(self.start_y, ey), max(self.start_y, ey)
        self.callback({"top": int(y1), "left": int(x1), "width": int(x2 - x1), "height": int(y2 - y1)})


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 控制台")
        self.geometry("380x380")
        self.attributes("-topmost", True)

        self.app_config = config.load_config()
        self.cloud_llm = CloudLLM(self.app_config)
        self.monitor_region = None
        self.is_monitoring = False
        self.is_processing = False
        self.last_text = ""
        self.is_hidden = False
        self.current_task_id = 0  # 当前翻译任务的唯一 ID
        self.context_memory = deque(maxlen=40)

        self.last_img = None
        self.is_dirty = False
        self.stable_count = 0

        self.setup_ui()
        self.process = psutil.Process()
        self.update_performance_info()

        generate_and_open_html()

        #try:
        #    self.hotkey_listener = keyboard.GlobalHotKeys({'<alt>+<space>': self.toggle_visibility})
        #    self.hotkey_listener.start()
        #except:
        #    pass

    def setup_ui(self):
        self.perf_label = ctk.CTkLabel(self, text="初始化...", font=("Arial", 10))
        self.perf_label.pack(pady=10)

        self.monitor_btn = ctk.CTkButton(self, text="⛶ 框选区域", command=self.toggle_monitor)
        self.monitor_btn.pack(pady=5)

        self.settings_btn = ctk.CTkButton(self, text="⚙️ 设置 API",
                                          command=lambda: SettingsWindow(self, self.app_config,
                                                                         self.save_settings_callback))
        self.settings_btn.pack(pady=5)

        self.hardcore_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self, text="硬核推理模式 (R1)", variable=self.hardcore_var).pack(pady=5)

        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        self.input_entry = ctk.CTkEntry(self.bottom_frame, placeholder_text="基于当前上下文追问...")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_question)
        self.send_btn = ctk.CTkButton(self.bottom_frame, text="提问", width=60, command=self.send_question)
        self.send_btn.pack(side="right")

    def toggle_visibility(self):
        if self.is_hidden:
            self.deiconify(); self.attributes("-topmost", True); self.is_hidden = False
        else:
            self.withdraw(); self.is_hidden = True

    def save_settings_callback(self, new_config):
        self.app_config = new_config
        config.save_config(self.app_config)
        self.cloud_llm = CloudLLM(self.app_config)

    def toggle_monitor(self):
        if not self.is_monitoring:
            ScreenSelector(self, self.start_monitoring)
        else:
            self.is_monitoring = False
            self.monitor_btn.configure(text="⛶ 框选区域", fg_color="#2b8a3e")

    def start_monitoring(self, region):
        self.monitor_region = region
        self.is_monitoring = True
        self.monitor_btn.configure(text="⏸ 暂停监控", fg_color="#c92a2a")
        broadcast_to_web("clear", "")

        self.last_img = None
        self.is_dirty = True
        self.stable_count = 2
        self.last_text = ""

        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def is_text_similar(self, text1, text2, threshold=0.90):
        if not text1 or not text2: return False
        if abs(len(text1) - len(text2)) > len(text1) * 0.2: return False
        return difflib.SequenceMatcher(None, text1, text2).ratio() > threshold

    def monitor_loop(self):
        while self.is_monitoring:
            with mss.mss() as sct:
                try:
                    sct_img = sct.grab(self.monitor_region)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                    gray_img = img.convert("L")
                    bw_img = gray_img.point(lambda x: 255 if x > 128 else 0)

                    if self.last_img is not None:
                        diff = ImageChops.difference(bw_img, self.last_img)
                        if ImageStat.Stat(diff).mean[0] > 1.0:
                            self.is_dirty = True
                            self.stable_count = 0
                        else:
                            if self.is_dirty:
                                self.stable_count += 1

                    self.last_img = bw_img

                    if self.is_dirty and self.stable_count >= 2:
                        text = pytesseract.image_to_string(gray_img, lang='eng').strip()

                        if len(text) > 20:
                            if not self.last_text or not self.is_text_similar(text, self.last_text, threshold=0.85):
                                print("\n[监控] 画面已稳定！强制中断旧翻译（如果有），极速启动新页面渲染...")
                                self.last_text = text
                                self.context_memory.append(text)

                                # === 【核心抢占逻辑】===
                                # 生成新的任务 ID，旧线程发现 ID 不匹配就会直接自尽
                                self.current_task_id += 1
                                self.start_cloud_translation(text, self.current_task_id)
                            else:
                                pass  # 画面变化但文本相似，忽略

                        self.is_dirty = False

                except Exception as e:
                    pass

            time.sleep(0.5)

    def start_cloud_translation(self, text, task_id):
        self.is_processing = True
        broadcast_to_web("clear", "")

        def run_task():
            try:
                # 【修复核心】：将 t 改为 is_thinking，与引擎底层的参数命名严格对齐！
                self.cloud_llm.translate_stream(
                    text,
                    lambda c, is_thinking=False: self.stream_to_web(c, is_thinking, task_id),
                    is_hardcore=self.hardcore_var.get()
                )
            except Exception:
                pass
            finally:
                # 只有当自己没有被新任务抢占时，才发送 done 信号
                if self.current_task_id == task_id:
                    self.is_processing = False
                    broadcast_to_web("done", "")

        threading.Thread(target=run_task, daemon=True).start()

    def stream_to_web(self, text_chunk, is_thinking=False, task_id=None):
        # 如果自己的 ID 已经过期，立刻抛出炸弹异常，让底层的 requests 停止下载数据！
        if task_id is not None and task_id != self.current_task_id:
            raise Exception("Aborted")

        broadcast_to_web("stream", text_chunk, is_thinking)

    def send_question(self, event=None):
        q = self.input_entry.get()
        if not q.strip(): return
        self.input_entry.delete(0, 'end')

        broadcast_to_web("question", q)
        memory_list = list(self.context_memory)

        def fetch_answer():
            ans = self.cloud_llm.ask(q, memory_list)
            broadcast_to_web("answer_done", ans)

        threading.Thread(target=fetch_answer, daemon=True).start()

    def update_performance_info(self):
        try:
            cpu, mem = self.process.cpu_percent(), self.process.memory_info().rss / 1024 / 1024
            self.perf_label.configure(text=f"状态: {'监控中' if self.is_monitoring else '待机'} | Mem: {int(mem)}MB")
        except:
            pass
        self.after(1000, self.update_performance_info)


if __name__ == "__main__":
    app = App()
    app.mainloop()