<template>
  <el-card class="memory-panel" shadow="never">
    <template #header>
      <div class="panel-title">诊断记忆</div>
    </template>

    <template v-if="hasMemory">
      <div class="memory-summary">
        <div>
          <span>最近诊断</span>
          <strong>{{ latestTime }}</strong>
        </div>
        <div>
          <span>历史记录</span>
          <strong>{{ history.length }} 条</strong>
        </div>
        <div>
          <span>持续薄弱项</span>
          <strong>{{ persistentWeak.length }} 个</strong>
        </div>
      </div>

      <div class="memory-section">
        <div class="section-title">最近几次薄弱知识点</div>
        <div class="history-list">
          <div v-for="record in history.slice(0, 5)" :key="record.diagnosed_at" class="history-row">
            <div class="history-time">{{ formatTime(record.diagnosed_at) }}</div>
            <div class="tag-list">
              <el-tag
                v-for="item in record.weak_concepts || []"
                :key="`${record.diagnosed_at}-${item.concept_id}`"
                type="danger"
                effect="plain"
              >
                {{ item.concept_name || item.concept_id }}
              </el-tag>
              <span v-if="!(record.weak_concepts || []).length" class="muted">暂无明显薄弱项</span>
            </div>
          </div>
        </div>
      </div>

      <div class="memory-section">
        <div class="section-title">掌握度变化简表</div>
        <el-table :data="masteryTrendRows" size="small" stripe>
          <el-table-column prop="concept_name" label="知识点" min-width="130" />
          <el-table-column prop="latest" label="最近" width="90">
            <template #default="{ row }">{{ row.latest.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="previous" label="上次" width="90">
            <template #default="{ row }">{{ row.previousText }}</template>
          </el-table-column>
          <el-table-column prop="delta" label="变化" width="90">
            <template #default="{ row }">
              <span :class="row.delta >= 0 ? 'delta-up' : 'delta-down'">{{ row.deltaText }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="memory-section">
        <div class="section-title">持续薄弱知识点</div>
        <div v-if="persistentWeak.length" class="tag-list">
          <el-tag v-for="item in persistentWeak" :key="item.concept_id" type="warning" effect="plain">
            {{ item.concept_name || item.concept_id }} × {{ item.count }}
          </el-tag>
        </div>
        <div v-else class="muted">暂无持续薄弱知识点</div>
      </div>
    </template>

    <div v-else class="empty-state">暂无历史诊断</div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  memory: {
    type: Object,
    default: null,
  },
  labels: {
    type: Object,
    default: () => ({}),
  },
})

const history = computed(() => props.memory?.history || [])
const shortMemory = computed(() => props.memory?.short_memory || null)
const hasMemory = computed(() => !!shortMemory.value || history.value.length > 0)
const latestRecord = computed(() => history.value[0] || shortMemory.value)
const latestTime = computed(() => formatTime(latestRecord.value?.diagnosed_at || latestRecord.value?.updated_at))

const persistentWeak = computed(() => {
  const counts = {}
  for (const record of history.value) {
    for (const item of record.weak_concepts || []) {
      const conceptId = item.concept_id
      if (!conceptId) continue
      if (!counts[conceptId]) {
        counts[conceptId] = {
          concept_id: conceptId,
          concept_name: item.concept_name || props.labels[conceptId] || conceptId,
          count: 0,
        }
      }
      counts[conceptId].count += 1
    }
  }
  return Object.values(counts).sort((left, right) => right.count - left.count)
})

const masteryTrendRows = computed(() => {
  const latest = history.value[0]?.mastery || shortMemory.value?.mastery || {}
  const previous = history.value[1]?.mastery || {}
  return Object.entries(latest).map(([conceptId, value]) => {
    const latestValue = Number(value) || 0
    const previousValue = previous[conceptId] == null ? null : Number(previous[conceptId])
    const delta = previousValue == null ? 0 : latestValue - previousValue
    return {
      concept_id: conceptId,
      concept_name: props.labels[conceptId] || conceptId,
      latest: latestValue,
      previous: previousValue,
      previousText: previousValue == null ? '暂无' : previousValue.toFixed(2),
      delta,
      deltaText: previousValue == null ? '暂无' : `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}`,
    }
  })
})

function formatTime(value) {
  if (!value) return '暂无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}
</script>

<style scoped>
.memory-panel {
  border-radius: 8px;
  border-color: #e3ecf7;
}

.memory-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.memory-summary > div {
  padding: 12px;
  border: 1px solid #e4edf7;
  border-radius: 8px;
  background: #fbfdff;
}

.memory-summary span,
.muted,
.history-time {
  color: #6b7c91;
  font-size: 13px;
}

.memory-summary strong {
  display: block;
  margin-top: 6px;
  color: #1769c2;
}

.memory-section {
  margin-top: 16px;
}

.section-title {
  margin-bottom: 10px;
  font-weight: 760;
  color: #173454;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-row {
  display: grid;
  grid-template-columns: 170px 1fr;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e4edf7;
  background: #fbfdff;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.delta-up {
  color: #168a45;
  font-weight: 700;
}

.delta-down {
  color: #d64545;
  font-weight: 700;
}

@media (max-width: 760px) {
  .memory-summary,
  .history-row {
    grid-template-columns: 1fr;
  }
}
</style>
