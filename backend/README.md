# EduCD-Agent

EduCD-Agent 是一个第一版 Python 命令行 Demo，用于演示“面向智慧教育认知诊断的思维链可解释智能体”后端链路：

学生答题数据 -> 简化 DINA 认知诊断 -> 知识点掌握度 -> Qwen 错因分析 -> Qwen 学情报告生成 -> 报告自检优化 -> 终端输出结果。

当前项目已进入第二阶段：在第一阶段 Python 命令行 Demo 基础上，新增 Flask 后端 API。
本阶段仍不包含 Vue 前端和数据库。

## 目录结构

```text
backend/
├── app.py
├── main.py
├── requirements.txt
├── data/
├── models/
├── agents/
├── tools/
└── memory/
```

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

## 第一阶段：运行命令行 Demo

进入后端目录：

```bash
cd EduCD-Agent/backend
python main.py
```

终端会输出：

- 当前学生 ID
- 当前是否为 mock 模式
- 知识点掌握度
- 错因分析 JSON
- 最终学情报告
- 班级薄弱知识点 Top3
- 高风险学生列表

## 第二阶段：运行 Flask 后端 API

安装依赖：

```bash
pip install -r requirements.txt
```

启动 Flask 后端：

```bash
python app.py
```

默认服务地址：

```text
http://127.0.0.1:5000
```

健康检查：

```text
http://127.0.0.1:5000/api/health
```

完整学生分析：

```text
http://127.0.0.1:5000/api/full-analysis/S001
```

常用接口：

- `GET /api/students`：获取学生列表
- `GET /api/questions`：获取题目列表
- `GET /api/diagnose/<student_id>`：获取学生知识点掌握度
- `GET /api/errors/<student_id>`：获取学生错题和错因分析
- `GET /api/report/<student_id>`：获取学生学情报告
- `GET /api/full-analysis/<student_id>`：获取完整学生分析
- `GET /api/class-summary`：获取班级诊断摘要
- `GET /api/cache/clear`：清空运行期内存缓存

第一次请求学生报告、错因分析或完整分析时会调用 Qwen，可能较慢；后续同一学生请求会走内存缓存。可以访问 `/api/cache/clear` 清除缓存。

如果没有配置 `DASHSCOPE_API_KEY`，或 Qwen API 调用失败，系统会自动进入 mock 模式，接口不会因为大模型调用失败而崩溃。

## 数据说明

`data/questions.json` 内置 8 道初中数学题，覆盖一元一次方程、等式性质、代数运算、三角形面积、二次方程、函数图像、分式运算和几何证明。

`data/responses.csv` 内置 5 名学生答题记录，其中 `S001` 同时包含正确题和错误题，便于观察错因分析与报告生成效果。
