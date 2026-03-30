import json
import threading
from google import genai
import os
import warnings
import traceback
import requests

# 忽略 urllib3 和 SSL 相关的警告
warnings.filterwarnings("ignore")

# 清空环境变量代理
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(k, None)


class LocalTranslator:
    def __init__(self):
        self.is_loaded = False

    def load_model(self):
        pass


class CloudLLM:
    def __init__(self, config):
        self.config = config

    def translate_stream(self, text, ui_callback, is_hardcore=False):
        model_type = self.config.get("active_model", "DeepSeek")
        keys = self.config.get("api_keys", {})
        api_key = keys.get(model_type, "")

        if not api_key:
            ui_callback(f"\n[错误] 请先配置 {model_type} 的 API Key", is_thinking=False)
            return

        # ==========================================
        # 🟢 【翻译通道】严苛版的提示词 (解决排版和废话问题)
        # ==========================================
        prompt = (
            "你是一个专业的学术翻译专家。请将原文翻译成准确、通顺的中文。\n"
            "【排版与输出最高指令（违背会导致系统崩溃）】：\n"
            "1. 绝不闲聊：绝对不要输出“好的”、“以下是翻译”等任何开场白或解释。直接、且仅仅输出翻译结果！\n"
            "2. 禁用代码块包裹：绝对不要使用 ```markdown 或 ``` 这样的代码块把整段翻译包裹起来！不要在段落首行使用空格缩进！\n"
            "3. 公式格式：行内公式严格使用 $ 包裹（如 $x=1$），独立公式使用 $$ 包裹。绝不能用 \\( 或 \\[。\n"
            "4. 结构清晰：保留原有的段落标题（如使用 ## 标题），保留列表等结构。\n\n"
            f"【原文】：\n{text}"
        )

        try:
            if model_type in ["DeepSeek", "Qwen"]:
                if model_type == "DeepSeek":
                    base_url = "https://" + "api" + ".deep" + "seek.com" + "/chat/completions"
                    model_name = "deepseek-reasoner" if is_hardcore else "deepseek-chat"
                else:
                    base_url = "https://" + "dash" + "scope.ali" + "yuncs.com" + "/compatible-mode/v1/chat/completions"
                    model_name = "qwen-max"

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True
                }

                response = requests.post(
                    base_url, headers=headers, json=data, stream=True,
                    verify=False, proxies={"http": "", "https": ""}, timeout=20
                )

                if response.status_code != 200:
                    ui_callback(f"\n[API 拒绝] 状态码: {response.status_code}, 详情: {response.text}",
                                is_thinking=False)
                    return

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line == "data: [DONE]":
                            break
                        if decoded_line.startswith("data: "):
                            try:
                                chunk = json.loads(decoded_line[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {})

                                if "reasoning_content" in delta and delta["reasoning_content"]:
                                    ui_callback(delta["reasoning_content"], is_thinking=True)
                                if "content" in delta and delta["content"]:
                                    ui_callback(delta["content"], is_thinking=False)
                            # === 【核心防阻塞机制】接收到打断信号，暴力掐断 TCP 连接 ===
                            except Exception as e:
                                if str(e) == "Aborted":
                                    response.close()
                                    return
                                else:
                                    raise e

            elif model_type == "Gemini":
                client = genai.Client(api_key=api_key, http_options={'verify': False})
                for chunk in client.models.generate_content_stream(model='gemini-1.5-pro', contents=prompt):
                    if chunk.text:
                        try:
                            ui_callback(chunk.text, is_thinking=False)
                        except Exception as e:
                            if str(e) == "Aborted": return

        except Exception as e:
            if str(e) != "Aborted":
                print("\n" + "=" * 40)
                traceback.print_exc()
                print("=" * 40 + "\n")
                ui_callback(f"\n[网络异常] {type(e).__name__}，请检查终端日志。", is_thinking=False)

        except Exception as e:
            print("\n" + "=" * 40)
            traceback.print_exc()
            print("=" * 40 + "\n")
            ui_callback(f"\n[网络层异常] {type(e).__name__}: 请查看 Pycharm 终端里的红色报错代码！", is_thinking=False)

    def ask(self, question, context_history=[]):
        model_type = self.config.get("active_model", "DeepSeek")
        keys = self.config.get("api_keys", {})
        api_key = keys.get(model_type, "")

        # 将记忆列表拼接成长文本
        full_context = "\n\n---历史阅读内容---\n\n".join(context_history)

        # ==========================================
        # 🔵 这里是【问答通道】专属的学术导师（费曼技巧）提示词
        # ==========================================
        prompt = (
            "你是一个顶级的资深架构师和学术导师，你的任务是解答学生的疑问，帮助其向专业领域进阶。\n"
            "【回答风格与约束（最高指令）】：\n"
            "1. 直奔主题：拒绝“好的，我来为您解答”等废话，直接给出核心结论。\n"
            "2. 专业与通俗的完美平衡：必须保留并使用原文献中的核心专业术语、英文缩写和数学符号，以帮助学生建立严谨的专业认知。但在首次引入或解释关键术语时，必须紧跟一句通俗易懂的简短解释或日常开发中的类比。\n"
            "3. 结构化输出：必须使用多级列表（Markdown）来组织内容，采用“核心结论 -> 专业原理解析（辅以通俗解释） -> 实例或推导”的逻辑链条。\n"
            "4. 格式要求：行内公式严格使用 $ 包裹，独立公式严格使用 $$ 包裹。包含代码时必须使用 Markdown 代码块。\n\n"
            f"【这是学生刚阅读过的近期上下文（仅供参考）】：\n{full_context}\n\n"
            f"【学生的问题】：{question}\n"
            "请直接输出解答，不要带任何开场白："
        )

        try:
            if model_type in ["DeepSeek", "Qwen"]:
                if model_type == "DeepSeek":
                    base_url = "https://" + "api" + ".deep" + "seek.com" + "/chat/completions"
                    model_name = "deepseek-chat"
                else:
                    base_url = "https://" + "dash" + "scope.ali" + "yuncs.com" + "/compatible-mode/v1/chat/completions"
                    model_name = "qwen-max"

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                }

                # 将超时时间延长到 120 秒，给 AI 充分的阅读长上下文和思考的时间
                response = requests.post(
                    base_url,
                    headers=headers,
                    json=data,
                    verify=False,
                    proxies={"http": "", "https": ""},
                    timeout=120
                )

                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    return f"API 拒绝请求: {response.status_code} - {response.text}"

            elif model_type == "Gemini":
                client = genai.Client(api_key=api_key, http_options={'verify': False})
                return client.models.generate_content(model='gemini-1.5-pro', contents=prompt).text
        except Exception as e:
            print("\n" + "=" * 40)
            traceback.print_exc()
            print("=" * 40 + "\n")
            return f"网络请求彻底失败: {type(e).__name__} (详情已打印至终端)"