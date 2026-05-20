<template>
  <div class="class-summary">
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-value">{{ knowledgeCount }}</div>
        <div class="metric-label">班级知识点数量</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ weakCount }}</div>
        <div class="metric-label">薄弱知识点 Top3 数量</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ riskCount }}</div>
        <div class="metric-label">风险学生数量</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ lowestScore }}</div>
        <div class="metric-label">最低平均掌握度</div>
      </div>
    </div>

    <el-card class="section" shadow="never">
      <template #header>
        <div class="panel-title">薄弱知识点排行</div>
      </template>
      <el-table :data="weakRows" stripe>
        <el-table-column prop="rank" label="排名" width="80" />
        <el-table-column prop="concept_name" label="知识点" min-width="140" />
        <el-table-column prop="concept_id" label="ID" width="100" />
        <el-table-column label="平均掌握度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(Number(row.average_mastery) * 100)" :stroke-width="8" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="section" shadow="never">
      <template #header>
        <div class="panel-title">风险学生列表</div>
      </template>
      <el-table v-if="riskDetails.length" :data="riskDetails" stripe>
        <el-table-column prop="student_name" label="学生" min-width="120">
          <template #default="{ row }">{{ row.student_name }}（{{ row.student_id }}）</template>
        </el-table-column>
        <el-table-column label="平均掌握度" width="150">
          <template #default="{ row }">{{ Number(row.average_mastery).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="薄弱知识点" min-width="220">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="item in row.weak_concepts" :key="item.concept_id" type="danger" effect="plain">
                {{ item.concept_name }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="risk-list">
        <el-tag v-for="student in summary.high_risk_students || []" :key="student" type="danger" effect="plain">
          {{ student }}
        </el-tag>
        <el-empty v-if="!(summary.high_risk_students || []).length" description="暂无风险学生" />
      </div>
    </el-card>

    <el-card class="section" shadow="never">
      <template #header>
        <div class="panel-title">教师教学建议</div>
      </template>
      <ul class="suggestion-list">
        <li v-for="item in teacherSuggestions" :key="item">{{ item }}</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({}),
  },
})

const averageMastery = computed(() => props.summary.class_average_mastery || {})
const weakTop3 = computed(() => props.summary.weak_concepts_rank || props.summary.weak_knowledge_top3 || [])
const riskDetails = computed(() => props.summary.high_risk_student_details || [])
const teacherSuggestions = computed(() => props.summary.teacher_suggestions || [])
const knowledgeCount = computed(() => Object.keys(averageMastery.value).length)
const weakCount = computed(() => weakTop3.value.length)
const riskCount = computed(() => riskDetails.value.length || (props.summary.high_risk_students || []).length)
const weakRows = computed(() =>
  weakTop3.value.map((item, index) => ({
    rank: index + 1,
    concept_id: item.concept_id || item.knowledge,
    concept_name: item.concept_name || item.knowledge,
    average_mastery: item.average_mastery,
  })),
)
const lowestScore = computed(() => {
  const values = Object.values(averageMastery.value)
  if (!values.length) return '0.00'
  return Math.min(...values.map(Number)).toFixed(2)
})
</script>

<style scoped>
.class-summary :deep(.el-card) {
  border-radius: 8px;
  border-color: #e3ecf7;
}

.risk-list,
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-list {
  margin: 0;
  padding-left: 18px;
  color: #2d425c;
  line-height: 1.9;
}
</style>
