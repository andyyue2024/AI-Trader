# GitHub 授权登录与模型集成需求文档

## 1. 项目背景

港大 AI-Trader 项目是一个基于多智能体（Multi-Agent）的交易模拟竞技平台，旨在通过不同 AI 模型在统一框架下的竞争，探索其在金融决策场景中的表现。当前项目依赖在 `.env` 文件中硬编码 API Key 来调用模型（如 DeepSeek）。为进一步丰富模型生态、降低用户配置成本，需要引入 **GitHub Copilot** 的模型能力，并采用 OAuth 设备授权流程实现安全、便捷的登录。

## 2. 用户需求

- 用户能够使用已有的 GitHub 账号授权登录，无需手动申请和维护多个 API Key。
- 授权成功后，用户可以在 AI-Trader 中无缝调用 GitHub Copilot 所支持的模型（如 Claude、GPT 系列等）。
- 支持在配置文件中指定使用哪些模型，并可混合使用原有的 API Key 方式与 GitHub 授权方式。
- 系统应提供清晰的首次授权引导，并在后续运行中自动使用已缓存的令牌。
- 令牌需安全存储，避免泄露。

## 3. 功能需求

| 需求 ID | 需求名称             | 描述                                                                                                                                                                                                 |
|--------|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| F01    | GitHub 设备授权登录   | 实现 OAuth 2.0 设备授权流程：用户运行命令后，终端显示验证码和授权网址；用户在浏览器中完成授权后，系统自动获取访问令牌。                                                                               |
| F02    | 本地令牌缓存与刷新     | 将获取到的访问令牌加密存储在本地文件（如 `~/.cache/ai-trader/github_token.json`），设置权限为仅所有者可读写；若令牌过期，自动尝试刷新（GitHub 令牌目前不会过期，但需考虑未来扩展）。               |
| F03    | 多模型配置支持         | 修改配置文件 `configs/default_config.json`，允许为每个模型指定认证方式（`auth_type`），新增 `github_oauth` 类型；模型名称前缀 `github-copilot/` 表示通过 GitHub Copilot 调用。                     |
| F04    | 模型调用统一接口       | 在 `agent/base_agent.py` 中扩展模型调用逻辑：若模型配置为 `github_oauth`，则从缓存加载 GitHub 令牌，构造对 GitHub Copilot API 的请求；否则保留原有 API Key 调用方式。                               |
| F05    | 错误处理与重试         | 当 GitHub 令牌失效或授权失败时，应提示用户重新授权，并引导执行授权流程；网络异常时应具备重试机制。                                                                                                   |
| F06    | 兼容性                 | 原有 API Key 方式必须继续支持，确保已有配置不受影响。                                                                                                                                                |
| F07    | 竞技场无缝集成         | 授权后获得的模型应能被 AI-Trader 的竞技场模块自动识别，无需额外修改竞技场逻辑。                                                                                                                       |

## 4. 非功能需求

| 需求 ID | 需求名称     | 描述                                                                                                                       |
|--------|--------------|----------------------------------------------------------------------------------------------------------------------------|
| NF01   | 安全性       | 访问令牌必须加密存储（可使用 Python `keyring` 或简单的文件加密）；配置文件中的 API Key 仍通过环境变量注入，避免硬编码。      |
| NF02   | 易用性       | 首次授权时提供清晰的终端提示，引导用户完成操作；令牌缓存后自动加载，用户无感知。                                           |
| NF03   | 可维护性     | 授权模块独立封装，与核心业务解耦；代码注释清晰，便于后续升级 GitHub OAuth 流程或更换认证方式。                           |
| NF04   | 性能         | 令牌加载仅在 Agent 初始化时进行一次，不影响模型推理性能；轮询授权状态时设置合理的间隔时间（如 5 秒），避免过多请求。       |
| NF05   | 兼容性       | 支持 Windows、macOS、Linux 主流操作系统，路径处理使用 `pathlib` 保证跨平台。                                                |

## 5. 用户场景示例

1. **首次使用**：用户克隆 AI-Trader 项目，运行 `python main.py`。系统检测到无 GitHub 令牌缓存，自动启动授权流程，终端显示：
   ```
   请访问 https://github.com/login/device
   并输入验证码：ABCD-EFGH
   ```
   用户在浏览器中登录 GitHub 并输入验证码后，终端提示授权成功，程序继续执行。

2. **后续使用**：用户再次运行程序，系统自动加载本地缓存令牌，直接使用已授权的模型进行交易决策。

3. **配置混合模型**：用户在 `default_config.json` 中同时配置：
   ```json
   {
     "models": [
       {"name": "github-copilot/claude-3.5-sonnet", "auth_type": "github_oauth"},
       {"name": "deepseek-chat", "api_key": "${DEEPSEEK_API_KEY}"}
     ]
   }
   ```
   竞技场将同时启动两个模型代理，分别使用 GitHub 授权和 API Key 方式调用。

---

# GitHub 授权登录与模型集成技术文档

## 1. 系统架构


    flowchart TB
        subgraph A[用户环境]
            direction TB
            A1[用户终端<br>启动AI-Trader]
            A2[本地配置文件<br>.env / config.json]
            A3[本地令牌存储<br>token_cache.json]
        end
    
        subgraph B[GitHub授权层<br>（借鉴OpenCode机制）]
            B1[OAuth设备授权流程<br>获取用户码/设备码]
            B2[令牌管理<br>加密存储/自动刷新]
        end
    
        subgraph C[AI-Trader核心系统]
            direction TB
            C1[main.py 主程序]
            C2[Agent层<br>base_agent.py]
            C3[MCP工具链]
            C4[工具实例]
        end
    
        subgraph D[GitHub Copilot服务]
            D1[OAuth端点<br>github.com/login/device]
            D2[Copilot API<br>模型调用接口]
        end
    
        subgraph E[外部数据服务]
            E1[Alpha Vantage<br>行情数据]
            E2[Jina AI<br>市场资讯]
        end
    
        A1 -->|1. 执行授权命令| B1
        B1 -->|2. 请求设备码| D1
        D1 -->|3. 返回用户码| B1
        B1 -->|4. 显示验证码| A1
        A1 -->|5. 用户访问并确认| D1
        B1 -->|6. 轮询授权状态| D1
        D1 -->|7. 返回访问令牌| B1
        B1 -->|8. 加密存储| A3
        
        A2 -->|9. 读取配置| C1
        A3 -->|10. 加载令牌| C2
        C1 -->|11. 初始化代理| C2
        C2 -->|12. 调用工具| C3
        C3 -->|13. 价格查询| C4
        C3 -->|14. 信息搜索| E2
        C3 -->|15. 交易执行| C4
        C2 -->|16. 模型推理| D2
        D2 -->|17. 返回决策| C2
        C4 -->|18. 获取数据| E1
（此处引用之前绘制的流程图，描述用户终端、GitHub授权层、AI-Trader核心、GitHub Copilot服务、外部数据服务之间的交互）

## 2. 模块设计

### 2.1 授权模块（`auth_github.py`）
- **职责**：实现 GitHub OAuth 设备授权流程，获取访问令牌；提供令牌的本地缓存与加载功能。
- **主要函数**：
  - `github_device_auth()`：执行完整授权流程，返回访问令牌。
  - `save_token(token)`：将令牌加密保存到本地文件。
  - `load_token()`：从本地文件加载令牌，若不存在或失效返回 `None`。
  - `refresh_token(refresh_token)`：预留刷新函数（目前 GitHub 令牌长期有效）。
- **依赖**：`requests`、`json`、`time`、`pathlib`、`cryptography`（可选，用于加密）。

### 2.2 配置模块（`configs/default_config.json`）
- 扩展模型配置字段：
  - `auth_type`：可选值 `"github_oauth"` 或 `"api_key"`（默认）。
  - `name`：模型标识，若为 `github_oauth` 类型，建议前缀 `github-copilot/`，便于识别。
  - `api_key`：仅在 `auth_type="api_key"` 时使用，支持 `${ENV_VAR}` 环境变量替换。

### 2.3 模型调用模块（`agent/base_agent.py`）
- **修改点**：
  - 在 `__init__` 中根据模型配置加载对应凭证。
  - 新增 `_build_github_client()` 方法，构造指向 GitHub Copilot API 的 HTTP 客户端。
  - 在 `chat_completion` 等方法中根据认证类型分发请求。
- **GitHub Copilot API 端点**：
  - 基础 URL：`https://api.github.com/copilot`
  - 具体模型调用路径：`/chat/completions`（需确认 GitHub 官方文档）
  - 请求头：`Authorization: token <access_token>`

### 2.4 令牌管理模块（`utils/token_manager.py`）
- 集中处理所有第三方服务的令牌存取，未来可扩展支持其他 OAuth 服务。
- 使用操作系统密钥环（keyring）或加密文件存储，提高安全性。 


