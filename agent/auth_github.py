import requests
import json
import time
from pathlib import Path
from cryptography.fernet import Fernet

CACHE_PATH = Path.home() / ".cache" / "ai-trader" / "github_token.json"
KEY_PATH = Path.home() / ".cache" / "ai-trader" / "key.bin"

class GitHubDeviceAuth:
    def __init__(self):
        self.token = None
        self.key = self._load_or_create_key()

    def github_device_auth(self):
        url = "https://github.com/login/device/code"
        client_id = self._get_client_id()
        data = {"client_id": client_id, "scope": "read:user copilot"}
        resp = requests.post(url, data=data, headers={"Accept": "application/json"})
        resp.raise_for_status()
        device_data = resp.json()
        print(f"请访问 {device_data['verification_uri']} 并输入验证码: {device_data['user_code']}")
        token_url = "https://github.com/login/oauth/access_token"
        for _ in range(60):
            time.sleep(device_data['interval'])
            token_resp = requests.post(token_url, data={
                "client_id": client_id,
                "device_code": device_data['device_code'],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            }, headers={"Accept": "application/json"})
            token_json = token_resp.json()
            if "access_token" in token_json:
                self.token = token_json["access_token"]
                self.save_token(self.token)
                print("授权成功！")
                return self.token
            elif token_json.get("error") == "authorization_pending":
                continue
            else:
                print("授权失败：", token_json)
                break
        return None

    def _get_client_id(self):
        import os
        client_id = os.environ.get("GITHUB_CLIENT_ID")
        if not client_id:
            raise ValueError("GITHUB_CLIENT_ID environment variable not set. Please set it to your GitHub OAuth application's client_id.")
        return client_id

    def save_token(self, token):
        encrypted = Fernet(self.key).encrypt(token.encode())
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            f.write(encrypted)

    def load_token(self):
        if not CACHE_PATH.exists():
            return None
        with open(CACHE_PATH, "rb") as f:
            encrypted = f.read()
        try:
            token = Fernet(self.key).decrypt(encrypted).decode()
            return token
        except Exception:
            return None

    def _load_or_create_key(self):
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if KEY_PATH.exists():
            with open(KEY_PATH, "rb") as f:
                return f.read()
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        return key

    def refresh_token(self, refresh_token):
        # Placeholder for future expansion
        pass
