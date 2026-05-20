<template>
  <div>
    <div class="panel-header">
      <div>
        <h1 class="page-title">教师看板</h1>
        <p class="page-desc">聚合班级知识点掌握情况，辅助教师发现共性薄弱点与风险学生。</p>
      </div>
      <div class="toolbar">
        <el-button :loading="training" @click="handleTrainDina">训练 DINA</el-button>
        <el-button type="primary" :loading="loading" @click="loadSummary">刷新数据</el-button>
      </div>
    </div>

    <section class="section status-strip">
      <el-tag :type="health?.qwen?.api_key_configured ? 'success' : 'info'" effect="plain">
        {{ health?.qwen?.status || 'Qwen 状态未知' }}
      </el-tag>
      <el-tag :type="health?.dina?.mastery_results_ready ? 'success' : 'warning'" effect="plain">
        DINA {{ health?.dina?.mastery_results_ready ? '已训练' : '未训练' }}
      </el-tag>
    </section>

    <el-alert
      v-if="serviceError"
      class="section"
      title="后端服务未连接或接口返回异常"
      :description="serviceError"
      type="error"
      show-icon
      :closable="false"
    />

    <div v-if="loading && !summary" class="section panel loading-panel">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-if="summary">
      <section class="section">
        <ClassSummaryPanel :summary="summary" />
      </section>

      <section class="section two-column">
        <MasteryChart :mastery="summary.class_average_mastery" :labels="conceptLabels" title="班级平均掌握度" />
        <el-card shadow="never" class="panel teacher-panel">
          <template #header>
            <div class="panel-title">教学干预优先级</div>
          </template>
          <div class="priority-list">
            <div v-for="item in weakRows" :key="item.concept_id" class="priority-row">
              <span>{{ item.concept_name }}</span>
              <strong>{{ Number(item.average_mastery).toFixed(2) }}</strong>
            </div>
          </div>
        </el-card>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { getApiErrorMessage, getClassSummary, getHealth, trainDina } from '../api'
import ClassSummaryPanel from '../components/ClassSummaryPanel.vue'
import MasteryChart from '../components/MasteryChart.vue'

const summary = ref(null)
const health = ref(null)
const loading = ref(false)
const training = ref(false)
const serviceError = ref('')

const conceptLabels = computed(() => {
  const labels = {}
  for (const item of summary.value?.class_average_mastery_detail || []) {
    labels[item.concept_id] = item.concept_name
  }
  return labels
})
const weakRows = computed(() => summary.value?.weak_concepts_rank || [])

async function loadHealth() {
  try {
    const response = await getHealth()
    if (response.success) health.value = response.data
  } catch {
    health.value = null
  }
}

async function loadSummary() {
  loading.value = true
  serviceError.value = ''
  try {
    const response = await getClassSummary()
    if (!response.success) {
      ElMessage.error(response.message || '获取班级摘要失败')
      return
    }
    summary.value = response.data
  } catch (error) {
    const message = getApiErrorMessage(error)
    serviceError.value = error.message || message
    ElMessage.error(message)
  } finally {
    loading.value = false
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
    await Promise.all([loadHealth(), loadSummary()])
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error))
  } finally {
    training.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadHealth(), loadSummary()])
})
</script>

<style scoped>
.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.loading-panel {
  padding: 24px;
}

.teacher-panel {
  padding: 18px;
}

.priority-list {
  display: grid;
  gap: 10px;
}

.priority-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e4edf7;
  border-radius: 8px;
  background: #fbfdff;
}

.priority-row span {
  color: #2d425c;
}

.priority-row strong {
  color: #d46b08;
}
</style>
