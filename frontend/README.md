# EduCD-Agent Frontend

第三阶段前端演示系统，基于 Vue 3、Vite、Element Plus、axios 和 ECharts 构建。

## 启动后端

前端启动前需要先运行 Flask 后端：

```bash
cd ../backend
python app.py
```

后端默认地址：

```text
http://127.0.0.1:5000
```

## 安装依赖

```bash
npm install
```

## 启动前端

```bash
npm run dev
```

前端默认开发地址通常为：

```text
http://127.0.0.1:5173
```

## 页面说明

- `/`：EduCD-Agent 首页
- `/student`：学生个体诊断
- `/teacher`：教师看板

如果页面提示“后端服务未连接，请先运行 python app.py”，请先确认 Flask 后端已经启动。
