from agent.auth_github import GitHubDeviceAuth

class TokenManager:
    def __init__(self):
        self.github_auth = GitHubDeviceAuth()

    def get_github_token(self):
        token = self.github_auth.load_token()
        if token:
            return token
        return self.github_auth.github_device_auth()

    def save_github_token(self, token):
        self.github_auth.save_token(token)

    def refresh_github_token(self, refresh_token):
        return self.github_auth.refresh_token(refresh_token)

