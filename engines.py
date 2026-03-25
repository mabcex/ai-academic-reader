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

        prompt = (
            "你是一个专业的学术翻译专家。请将这段教材内容翻译成准确、专业的中文。\n"
            "【排版格式最高指令】：\n"
            "1. 所有的行内数学公式必须严格使用单个 $ 包裹（例如：$a=b$）。\n"
            "2. 所有的独立数学公式必须严格使用双 $$ 包裹。\n"
            "3. 绝对禁止使用 \\( \\) 或 \\[ \\] 来包裹公式，否则会导致系统崩溃！\n"
            "4. 如果原文包含任何编程代码、终端命令（如 pip, python --version 等）或变量名，你必须使用 Markdown 的代码块（```）或行内代码（`）将其严格包裹起来。\n"
            f"\n原文内容：\n{text}"
        )

        try:
            if model_type in ["DeepSeek", "Qwen"]:
                # 【防篡改终极碎渣拼接法】：彻底击败智能复制
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

                # 强行绕过所有 VPN 和证书
                response = requests.post(
                    base_url,
                    headers=headers,
                    json=data,
                    stream=True,
                    verify=False,
                    proxies={"http": "", "https": ""},
                    timeout=20  # 流式请求首字节超时时间
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
                            except json.JSONDecodeError:
                                pass

            elif model_type == "Gemini":
                client = genai.Client(api_key=api_key, http_options={'verify': False})
                for chunk in client.models.generate_content_stream(model='gemini-1.5-pro', contents=prompt):
                    if chunk.text: ui_callback(chunk.text, is_thinking=False)

        except Exception as e:
            print("\n" + "=" * 40)
            traceback.print_exc()
            print("=" * 40 + "\n")
            ui_callback(f"\n[网络层异常] {type(e).__name__}: 请查看 Pycharm 终端里的红色报错代码！", is_thinking=False)

    def ask(self, question, context_history=[]):
        model_type = self.config.get("active_model", "DeepSeek")
        keys = self.config.get("api_keys", {})
        api_key = keys.get(model_type, "")
        full_context = "\n\n---历史阅读内容---\n\n".join(context_history)

        prompt = (
            "你是一个严谨的学术导师。请根据提供的阅读上下文，详细解答学生的问题。\n"
            "【排版格式最高指令】：行内公式严格使用 $ 包裹，独立公式严格使用 $$ 包裹。包含代码时必须使用 Markdown 代码块。\n\n"
            f"【近期阅读上下文】：\n{full_context}\n\n"
            f"【学生的问题】：{question}\n请解答："
        )

        try:
            if model_type in ["DeepSeek", "Qwen"]:
                # 【防篡改终极碎渣拼接法】
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

                # 【修复核心】：将超时时间延长到 120 秒，给 AI 充分的阅读 5 页上下文和思考的时间
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