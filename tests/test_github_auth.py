import unittest
from agent.auth_github import GitHubDeviceAuth

class TestGitHubDeviceAuth(unittest.TestCase):
    def test_device_auth_flow(self):
        auth = GitHubDeviceAuth()
        token = auth.github_device_auth()
        self.assertIsNotNone(token)

    def test_token_storage(self):
        auth = GitHubDeviceAuth()
        test_token = "testtoken123"
        auth.save_token(test_token)
        loaded = auth.load_token()
        self.assertEqual(loaded, test_token)

if __name__ == "__main__":
    unittest.main()

