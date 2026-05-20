# 面向智慧教育认知诊断的思维链可解释智能体

EduCD-Agent 是一个面向智慧教育场景的认知诊断可解释智能体原型。

本项目围绕“学生答题数据如何转化为可解释学情报告”这一核心问题，构建了一个融合认知诊断模型与大语言模型的智能体系统。系统首先基于学生答题记录和题目知识点 Q 矩阵，利用 DINA 认知诊断模型计算学生在不同知识点上的掌握程度；随后调用 Qwen Api，对学生错题进行错因分析、思维断点定位和个性化学习建议生成；最后形成结构化学情报告，并在前端页面中进行可视化展示。

系统不仅支持学生个体诊断，还支持教师端班级诊断摘要展示，包括班级薄弱知识点、高风险学生列表和教学干预建议，形成从“答题数据 → 认知诊断 → 错因解释 → 学情报告 → 教学干预”的智慧教育闭环。

---

```bash
# 进入后端目录
cd EduCD-Agent/backend

# 安装后端依赖
pip install -r requirements.txt

# 配置 Qwen API Key
$env:DASHSCOPE_API_KEY="你的APIKey"

# 训练 DINA 模型
python train_dina.py

# 运行后端
python app.py

# 进入前端目录
cd EduCD-Agent/frontend

# 安装前端依赖
npm install

# 运行前端
npm run dev
```

---
