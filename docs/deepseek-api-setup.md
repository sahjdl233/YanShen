# OpenAI-compatible API 配置教程

研申不绑定 DeepSeek。任何兼容 OpenAI **Chat Completions** 和 `/v1/models` 的服务都可以使用，例如 DeepSeek、硅基流动、OpenRouter、阿里云百炼、火山方舟或自建网关。

## 1. 获取服务商配置

1. 登录模型服务商控制台，创建 API Key。
2. 找到它的 **OpenAI-compatible Base URL**，必须是 API 域名，不是网页聊天地址。
3. 记录要使用的模型 ID。

常见形式：

- `https://api.deepseek.com` → 系统会请求 `/chat/completions`
- `https://api.example.com/v1` → 系统会请求 `/v1/chat/completions` 和 `/v1/models`
- `https://api.example.com/v4` → 系统会请求 `/v4/chat/completions` 和 `/v4/models`

## 2. 在“研申”中配置

打开 **设置** 页：

- 运行模式：`API 自动模式`
- 服务商名称：自定义，例如 `SiliconFlow`
- Base URL：填写服务商的 OpenAI-compatible 地址
- 模型名：先填一个，或点击“获取模型列表”后从自动补全中选择
- Temperature：通常保持 `0.2`

## 3. API Key 与环境变量

直接把密钥粘贴到 **API Key** 输入框即可。

**API Key 环境变量**不是密钥本身，而是存放密钥的系统变量名称。例如你执行过：

```powershell
setx EXAMPLE_API_KEY "sk-..."
```

设置页就填写：

- API Key：留空
- API Key 环境变量：`EXAMPLE_API_KEY`

如果两者都填了，界面里的 **API Key** 优先。不要把 Key 写进截图、仓库、导出文件或聊天记录。

## 4. 测试和获取模型列表

设置页新增了两个按钮：

- **测试连接**：发送一条极小的 Chat Completions 测试消息。
- **获取模型列表**：请求 `/models`；如果服务商不支持该接口，仍可手动填写模型 ID。

## 5. 常见错误

- **HTTP 403 / error code 1010**：确认用的是 API Base URL 而不是网页地址；部分防火墙会拦截默认脚本 User-Agent，研申已改为浏览器风格 UA 并附带标准 Accept 头。若仍 403，请联系服务商确认域名、地域或访问策略。
- **HTTP 401/403 且提示 invalid key**：检查 Key、额度、模型授权和 Base URL。
- **HTTP 404**：Base URL 缺少版本路径，或服务商的路径不是 OpenAI-compatible。
- **返回格式无法解析**：该地址可能只是网页或代理网关，不是 Chat Completions API。
