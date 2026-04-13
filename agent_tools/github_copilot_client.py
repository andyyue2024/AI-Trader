import requests
from agent.auth_github import GitHubDeviceAuth

class GithubCopilotClient:
    def __init__(self, token=None):
        self.api_base = "https://api.githubcopilot.com"
        self.models_api_base = "https://models.github.ai"
        self.token = token or GitHubDeviceAuth().load_token() or GitHubDeviceAuth().github_device_auth()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Copilot-Integration-Id": "ai-trader-agent"
        }
        self.models_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10"
        }

    def refresh_token(self):
        self.token = GitHubDeviceAuth().github_device_auth()
        self.headers["Authorization"] = f"Bearer {self.token}"
        self.models_headers["Authorization"] = f"Bearer {self.token}"

    def chat_completion(self, prompt, model="gpt-4o", system_prompt=None):
        url = f"{self.api_base}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        try:
            resp = requests.post(url, headers=self.headers, json=data, timeout=30)
            if resp.status_code == 401:
                print("Copilot令牌无效或过期，尝试重新授权...")
                self.refresh_token()
                resp = requests.post(url, headers=self.headers, json=data, timeout=30)
            if resp.status_code == 400:
                print(f"Copilot 400 Bad Request: {resp.text}")
            resp.raise_for_status()
            result = resp.json()
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
            else:
                print("⚠️ Copilot API返回格式异常，已采用mock返回。")
        except Exception as e:
            print(f"❌ Copilot API调用失败: {e}，已采用mock返回。")
        return f"[Mock Copilot] {prompt}"

    def get_available_models(self):
        url = f"{self.models_api_base}/catalog/models"
        try:
            response = requests.get(url, headers=self.models_headers, timeout=15)
            if response.status_code == 401:
                print("Copilot令牌无效或过期，尝试重新授权...")
                self.refresh_token()
                response = requests.get(url, headers=self.models_headers, timeout=15)
            response.raise_for_status()
            models_data = response.json()

            # Catalog endpoint usually returns a top-level list.
            if isinstance(models_data, list):
                return [model.get("id") for model in models_data if isinstance(model, dict) and model.get("id")]

            # Fallback for wrapped response formats.
            if isinstance(models_data, dict):
                data_list = models_data.get("data", [])
                if isinstance(data_list, list):
                    return [model.get("id") for model in data_list if isinstance(model, dict) and model.get("id")]
            return []
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

    def ask(self, prompt, model="gpt-4o", system_prompt=None):
        return self.chat_completion(prompt, model=model, system_prompt=system_prompt)

