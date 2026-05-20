<template>
  <div class="home-page">
    <section class="hero panel">
      <div class="hero-content">
        <el-tag type="primary" effect="plain">大创项目演示原型</el-tag>
        <h1 class="page-title">面向智慧教育认知诊断的思维链可解释智能体</h1>
        <p class="page-desc">
          基于认知诊断模型与 Qwen 大模型，实现从学生答题数据到错因分析、学情报告和教师教学建议的闭环。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push('/student')">学生诊断</el-button>
          <el-button size="large" @click="router.push('/teacher')">教师看板</el-button>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="signal-card">
          <span>诊断链路</span>
          <strong>5 步闭环</strong>
        </div>
        <div class="signal-card">
          <span>解释维度</span>
          <strong>错因 + 建议</strong>
        </div>
        <div class="signal-card">
          <span>运行模式</span>
          <strong>Qwen / Mock</strong>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="panel-header">
        <h2 class="panel-title">技术路线</h2>
      </div>
      <div class="route-grid">
        <div v-for="(item, index) in routeCards" :key="item.title" class="route-card">
          <div class="step-index">{{ String(index + 1).padStart(2, '0') }}</div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const routeCards = [
  { title: '学生答题数据', desc: '读取题目、Q 矩阵和学生作答记录，形成诊断输入。' },
  { title: 'DINA 认知诊断', desc: '计算各知识点掌握度，定位学生个体薄弱环节。' },
  { title: 'Qwen 错因分析', desc: '结合错题、答案和知识库生成可解释错因 JSON。' },
  { title: '学情报告生成', desc: '汇总掌握度和错因，输出结构化中文学情报告。' },
  { title: '教师教学干预', desc: '基于班级薄弱知识点和高风险学生辅助教学决策。' },
]
</script>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 24px;
  padding: 34px;
  align-items: stretch;
}

.hero-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero .page-title {
  margin-top: 16px;
  max-width: 780px;
  font-size: 34px;
  line-height: 1.25;
}

.hero-actions {
  margin-top: 28px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-metrics {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.signal-card {
  padding: 18px;
  border-radius: 8px;
  border: 1px solid #dce8f6;
  background: #f8fbff;
}

.signal-card span {
  display: block;
  color: #6b7d94;
  font-size: 13px;
}

.signal-card strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  color: #1769c2;
}

.route-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.route-card {
  min-height: 190px;
  padding: 18px;
  border: 1px solid #e2ebf5;
  border-radius: 8px;
  background: #fff;
}

.step-index {
  color: #2f80ed;
  font-size: 13px;
  font-weight: 760;
}

.route-card h3 {
  margin: 14px 0 10px;
  color: #132948;
  font-size: 18px;
}

.route-card p {
  margin: 0;
  color: #65768d;
  line-height: 1.75;
}

@media (max-width: 980px) {
  .hero,
  .route-grid {
    grid-template-columns: 1fr;
  }
}
</style>
