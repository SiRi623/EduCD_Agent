## 安装依赖

建议在 `EduCD-Agent/backend` 目录下创建虚拟环境后安装依赖：

```bash
pip install -r requirements.txt
```

## 配置 DASHSCOPE_API_KEY

如果需要调用真实 Qwen API，请配置环境变量：

```bash
set DASHSCOPE_API_KEY=你的DashScope API Key
```

PowerShell 可使用：

```powershell
$env:DASHSCOPE_API_KEY="你的DashScope API Key"
```

程序会使用 OpenAI 兼容接口：

- base_url: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 默认模型: `qwen-plus`

如果未检测到 `DASHSCOPE_API_KEY`，或真实调用失败，系统会自动进入 mock 模式，保证 Demo 不崩溃并能输出完整诊断结果。
