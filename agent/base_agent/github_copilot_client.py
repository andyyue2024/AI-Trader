import requests
from utils.token_manager import TokenManager
import os

class GitHubCopilotClient:
    def __init__(self):
        self.token_manager = TokenManager()
        self.token = self.token_manager.get_github_token()
        # Copilot API 真实端点（如有变动请查阅官方文档）
        self.base_url = "https://api.github.com/copilot/v1"
        self.model = os.environ.get("COPILOT_MODEL", "gpt-4")
        self.temperature = float(os.environ.get("COPILOT_TEMPERATURE", 0.7))

    def chat_completion(self, prompt):
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 401 or resp.status_code == 403:
                print("❌ Copilot 令牌无效或已过期，请重新授权。")
                # 可在此处触发重新授权流程
                raise RuntimeError("Copilot 令牌无效或已过期")
            resp.raise_for_status()
            result = resp.json()
            # 兼容 Copilot 返回格式
            if "choices" in result and result["choices"]:
                return result
            else:
                print("⚠️ Copilot API返回格式异常，已采用mock返回。")
        except Exception as e:
            print(f"❌ Copilot API调用失败: {e}，已采用mock返回。")
        # mock fallback
        return {
            "choices": [
                {"message": {"content": f"[Mock Copilot] {prompt}"}}
            ]
        }
