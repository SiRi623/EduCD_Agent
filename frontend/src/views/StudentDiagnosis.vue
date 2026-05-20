<template>
  <div>
    <div class="panel-header">
      <div>
        <h1 class="page-title">学生个体诊断</h1>
        <p class="page-desc">基于 DINA 掌握度、Q 矩阵错题证据和 Qwen Agent 生成可解释学情报告。</p>
      </div>
      <div class="toolbar">
        <el-select v-model="selectedStudent" placeholder="选择学生" filterable style="width: 220px">
          <el-option
            v-for="student in students"
            :key="student.student_id"
            :label="student.label"
            :value="student.student_id"
          />
        </el-select>
        <el-button type="primary" :loading="loading" @click="runDiagnosis">开始诊断</el-button>
        <el-button :loading="training" @click="handleTrainDina">训练 DINA</el-button>
        <el-button @click="handleClearCache">清除缓存</el-button>
        <el-button @click="handleClearMemory">清空记忆</el-button>
      </div>
    </div>

    <section class="section status-strip">
      <el-tag :type="health?.qwen?.api_key_configured ? 'success' : 'info'" effect="plain">
        {{ health?.qwen?.status || 'Qwen 状态未知' }}
      </el-tag>
      <el-tag :type="health?.dina?.mastery_results_ready ? 'success' : 'warning'" effect="plain">
        DINA {{ health?.dina?.mastery_results_ready ? '已训练' : '未训练' }}
      </el-tag>
      <el-tag v-if="analysis?.student_name" effect="plain">
        当前学生：{{ analysis.student_name }}（{{ analysis.student_id }}）
      </el-tag>
    </section>

    <el-alert
      v-if="serviceError"
      class="section"
      :title="serviceErrorTitle"
      :description="serviceError"
      type="error"
      show-icon
      :closable="false"
    />

    <el-card v-if="!analysis" class="section panel" shadow="never">
      <div class="empty-state">请选择学生并点击“开始诊断”</div>
    </el-card>

    <template v-if="analysis">
      <section class="section metric-grid">
        <div class="metric-card">
          <div class="metric-value">{{ analysis.student_name || analysis.student_id }}</div>
          <div class="metric-label">学生</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ masteryCount }}</div>
          <div class="metric-label">知识点数量</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ weakPoints.length }}</div>
          <div class="metric-label">薄弱知识点数量</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ analysis.wrong_questions.length }}</div>
          <div class="metric-label">错题数量</div>
        </div>
      </section>

      <section class="section two-column">
        <MasteryChart :mastery="analysis.mastery" :labels="conceptLabels" title="DINA 知识点掌握度" />
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-title">薄弱知识点列表</div>
          </template>
          <div v-if="weakPoints.length" class="weak-list">
            <div v-for="item in weakPoints" :key="item.concept_id" class="weak-row">
              <div>
                <strong>{{ item.concept_name }}</strong>
                <span>{{ item.concept_id }}</span>
              </div>
              <el-progress :percentage="Math.round(item.score * 100)" :stroke-width="9" />
            </div>
          </div>
          <el-empty v-else description="暂无薄弱知识点" />
        </el-card>
      </section>

      <section class="section">
        <MemoryPanel :memory="memory" :labels="conceptLabels" />
      </section>

      <section class="section">
        <div class="panel-header">
          <h2 class="panel-title">CoT 错因分析</h2>
        </div>
        <div v-if="analysis.error_analysis.length" class="error-list">
          <ErrorAnalysisCard
            v-for="error in analysis.error_analysis"
            :key="`${error.question_id}-${error.error_type}`"
            :error="error"
          />
        </div>
        <el-card v-else shadow="never" class="panel">
          <el-empty description="该学生暂无错题分析" />
        </el-card>
      </section>

      <section class="section">
        <ReportPanel :report="analysis.report" :structured-report="analysis.structured_report" />
      </section>
    </template>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import {
  clearCache,
  clearMemory,
  getApiErrorMessage,
  getFullAnalysis,
  getHealth,
  getStudentMemory,
  getStudents,
  getStudentsDetail,
  trainDina,
} from '../api'
import ErrorAnalysisCard from '../components/ErrorAnalysisCard.vue'
import MasteryChart from '../components/MasteryChart.vue'
import MemoryPanel from '../components/MemoryPanel.vue'
import ReportPanel from '../components/ReportPanel.vue'

const students = ref([])
const selectedStudent = ref('S001')
const analysis = ref(null)
const memory = ref(null)
const health = ref(null)
const loading = ref(false)
const training = ref(false)
const serviceError = ref('')
const serviceErrorTitle = ref('')

const masteryCount = computed(() => Object.keys(analysis.value?.mastery || {}).length)
const conceptLabels = computed(() => {
  const labels = {}
  for (const item of analysis.value?.structured_report?.mastery_summary || []) {
    labels[item.concept_id] = item.concept_name
  }
  return labels
})
const weakPoints = computed(() => {
  const structuredWeak = analysis.value?.structured_report?.weak_concepts || []
  if (structuredWeak.length) {
    return structuredWeak.map((item) => ({
      concept_id: item.concept_id,
      concept_name: item.concept_name || item.concept_id,
      score: Number(item.mastery ?? 0),
    }))
  }
  return Object.entries(analysis.value?.mastery || {})
    .filter(([, score]) => Number(score) < 0.6)
    .map(([conceptId, score]) => ({
      concept_id: conceptId,
      concept_name: conceptLabels.value[conceptId] || conceptId,
      score: Number(score),
    }))
})

async function loadHealth() {
  try {
    const response = await getHealth()
    if (response.success) health.value = response.data
  } catch {
    health.value = null
  }
}

async function loadStudents() {
  try {
    serviceError.value = ''
    const response = await getStudentsDetail()
    if (response.success) {
      students.value = response.data || []
    } else {
      const fallback = await getStudents()
      students.value = (fallback.data || []).map((id) => ({ student_id: id, student_name: id, label: id }))
    }
    if (!students.value.some((student) => student.student_id === selectedStudent.value)) {
      selectedStudent.value = students.value[0]?.student_id || ''
    }
  } catch (error) {
    const message = getApiErrorMessage(error)
    serviceErrorTitle.value = message
    serviceError.value = error.message || message
    ElMessage.error(message)
  }
}

async function runDiagnosis() {
  if (!selectedStudent.value) {
    ElMessage.warning('请先选择学生')
    return
  }
  loading.value = true
  serviceError.value = ''
  try {
    const response = await getFullAnalysis(selectedStudent.value)
    if (!response.success) {
      ElMessage.error(response.message || '诊断失败')
      return
    }
    analysis.value = response.data
    memory.value = response.data.memory || null
    await loadMemory(selectedStudent.value)
    ElMessage.success('诊断完成')
  } catch (error) {
    const message = getApiErrorMessage(error)
    serviceErrorTitle.value = message
    serviceError.value = error.message || message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

async function loadMemory(studentId) {
  if (!studentId) return
  try {
    const response = await getStudentMemory(studentId)
    if (response.success) memory.value = response.data
  } catch {
    memory.value = null
  }
}

async function handleTrainDina() {
  training.value = true
  try {
    const response = await trainDina()
    if (!response.success) {
      ElMessage.error(response.message || 'DINA 训练失败')
      return
    }
    ElMessage.success('DINA 训练完成')
    await loadHealth()
    if (selectedStudent.value) await runDiagnosis()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error))
  } finally {
    training.value = false
  }
}

async function handleClearCache() {
  try {
    const response = await clearCache()
    if (!response.success) {
      ElMessage.error(response.message || '清除缓存失败')
      return
    }
    ElMessage.success('缓存已清空')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error))
  }
}

async function handleClearMemory() {
  try {
    const response = await clearMemory()
    if (!response.success) {
      ElMessage.error(response.message || '清空记忆失败')
      return
    }
    memory.value = null
    ElMessage.success('诊断记忆已清空')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error))
  }
}

onMounted(async () => {
  await Promise.all([loadHealth(), loadStudents()])
  await loadMemory(selectedStudent.value)
})

watch(selectedStudent, async (studentId) => {
  memory.value = null
  await loadMemory(studentId)
})
</script>

<style scoped>
.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.weak-list,
.error-list {
  display: grid;
  gap: 12px;
}

.weak-row {
  display: grid;
  grid-template-columns: minmax(110px, 0.75fr) minmax(120px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid #e4edf7;
  border-radius: 8px;
  background: #fbfdff;
}

.weak-row strong,
.weak-row span {
  display: block;
}

.weak-row span {
  margin-top: 3px;
  color: #708095;
  font-size: 12px;
}

@media (max-width: 760px) {
  .weak-row {
    grid-template-columns: 1fr;
  }
}
</style>
