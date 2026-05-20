<template>
  <el-card class="report-panel" shadow="never">
    <template #header>
      <div class="report-title">个性化学情报告</div>
    </template>

    <template v-if="hasStructuredReport">
      <el-alert
        class="report-alert"
        :title="structuredReport.overall_diagnosis || '暂无总体结论'"
        type="info"
        :closable="false"
        show-icon
      />

      <div class="report-section">
        <div class="section-title">知识点掌握情况</div>
        <div class="mastery-list">
          <div v-for="item in structuredReport.mastery_summary || []" :key="item.concept_id" class="mastery-row">
            <div>
              <strong>{{ item.concept_name || item.concept_id }}</strong>
              <span>{{ item.level || levelText(item.mastery) }}</span>
            </div>
            <el-progress :percentage="toPercent(item.mastery)" :stroke-width="10" :show-text="false" />
            <em>{{ Number(item.mastery ?? 0).toFixed(2) }}</em>
          </div>
        </div>
      </div>

      <div class="report-section">
        <div class="section-title">主要薄弱知识点</div>
        <div v-if="weakConcepts.length" class="tag-list">
          <el-tag v-for="item in weakConcepts" :key="item.concept_id" type="danger" effect="plain">
            {{ item.concept_name || item.concept_id }}：{{ Number(item.mastery ?? 0).toFixed(2) }}
          </el-tag>
        </div>
        <div v-else class="inline-empty">暂无明显薄弱知识点</div>
      </div>

      <div class="report-section">
        <div class="section-title">典型错因分析</div>
        <el-timeline v-if="errorItems.length">
          <el-timeline-item v-for="item in errorItems" :key="item.question_id" :timestamp="item.question_id">
            <strong>{{ item.error_type }}</strong>
            <p>{{ item.error_reason }}</p>
            <p class="muted">认知断点：{{ item.cognitive_breakpoint }}</p>
          </el-timeline-item>
        </el-timeline>
        <div v-else class="inline-empty">暂无错因分析</div>
      </div>

      <div class="report-section two-list">
        <div>
          <div class="section-title">学习建议</div>
          <ul>
            <li v-for="item in structuredReport.personalized_suggestions || []" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div>
          <div class="section-title">练习路径</div>
          <ul>
            <li v-for="item in structuredReport.practice_path || []" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>

      <div v-if="structuredReport.self_check" class="report-section self-check">
        <div class="section-title">Reflection 自检</div>
        <div class="check-grid">
          <el-tag :type="structuredReport.self_check.is_consistent_with_cdm ? 'success' : 'danger'">
            CDM 一致性
          </el-tag>
          <el-tag :type="structuredReport.self_check.has_specific_error_reason ? 'success' : 'danger'">
            具体错因
          </el-tag>
          <el-tag :type="structuredReport.self_check.has_actionable_suggestion ? 'success' : 'danger'">
            可执行建议
          </el-tag>
          <el-tag :type="!structuredReport.self_check.has_vague_expression ? 'success' : 'warning'">
            空泛表达检查
          </el-tag>
        </div>
        <p class="muted">{{ structuredReport.reflection_summary }}</p>
      </div>
    </template>

    <div v-else-if="report" class="report-content">{{ report }}</div>
    <div v-else class="empty-state">暂无报告</div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: {
    type: String,
    default: '',
  },
  structuredReport: {
    type: Object,
    default: null,
  },
})

const hasStructuredReport = computed(() => !!props.structuredReport)
const weakConcepts = computed(() => props.structuredReport?.weak_concepts || [])
const errorItems = computed(() => props.structuredReport?.typical_error_analysis || [])

function toPercent(value) {
  return Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100)
}

function levelText(value) {
  const score = Number(value) || 0
  if (score >= 0.8) return '掌握较好'
  if (score >= 0.6) return '基本掌握'
  if (score >= 0.4) return '掌握不稳'
  return '明显薄弱'
}
</script>

<style scoped>
.report-panel {
  border-radius: 8px;
  border-color: #e3ecf7;
}

.report-title {
  font-size: 18px;
  font-weight: 700;
  color: #132948;
}

.report-alert {
  margin-bottom: 18px;
}

.report-section {
  margin-top: 18px;
}

.section-title {
  margin-bottom: 10px;
  font-weight: 760;
  color: #173454;
}

.mastery-list {
  display: grid;
  gap: 10px;
}

.mastery-row {
  display: grid;
  grid-template-columns: minmax(160px, 0.9fr) minmax(140px, 1fr) 52px;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e5eef8;
  background: #fbfdff;
}

.mastery-row strong,
.mastery-row span {
  display: block;
}

.mastery-row span,
.muted {
  color: #6b7c91;
  font-size: 13px;
}

.mastery-row em {
  font-style: normal;
  font-weight: 700;
  color: #1769c2;
  text-align: right;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.two-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

ul {
  margin: 0;
  padding-left: 18px;
  color: #2d425c;
  line-height: 1.9;
}

.check-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.inline-empty {
  color: #7b8aa0;
  padding: 12px;
  border-radius: 8px;
  background: #fbfdff;
  border: 1px dashed #d2dfed;
}

.report-content {
  white-space: pre-wrap;
  line-height: 1.9;
  color: #253a54;
  font-size: 15px;
}

@media (max-width: 760px) {
  .mastery-row,
  .two-list {
    grid-template-columns: 1fr;
  }

  .mastery-row em {
    text-align: left;
  }
}
</style>
