<template>
  <el-card class="error-card" shadow="never">
    <template #header>
      <div class="error-header">
        <div>
          <span class="question-id">{{ error.question_id || '未知题号' }}</span>
          <el-tag class="type-tag" size="small" type="warning">{{ error.error_type || 'Unknown' }}</el-tag>
          <el-tag class="type-tag" size="small" type="info">{{ difficultyText }}</el-tag>
        </div>
        <el-tag size="small" type="success">置信度 {{ confidenceText }}</el-tag>
      </div>
    </template>

    <div class="cot-policy">
      <div>
        <span class="field-label">动态 CoT 策略</span>
        <strong>{{ cotStrategy.label || '中等题标准链' }}</strong>
      </div>
      <span>{{ reasoningSteps.length }} / {{ cotStrategy.target_steps || reasoningSteps.length }} 步</span>
    </div>

    <div class="tag-row">
      <span class="field-label">薄弱知识点</span>
      <el-tag v-for="item in weakKnowledge" :key="item" effect="plain">{{ item }}</el-tag>
    </div>

    <div v-if="conceptRows.length" class="concept-grid">
      <div v-for="item in conceptRows" :key="item.concept_id" class="concept-chip">
        <span>{{ item.concept_name || item.concept_id }}</span>
        <strong>{{ Number(item.mastery ?? 0).toFixed(2) }}</strong>
      </div>
    </div>

    <el-descriptions :column="1" border class="analysis-desc">
      <el-descriptions-item label="认知断点">
        {{ error.cognitive_breakpoint || error.thinking_breakpoint || '暂无' }}
      </el-descriptions-item>
      <el-descriptions-item label="错误原因">
        {{ error.error_reason || error.reason || '暂无' }}
      </el-descriptions-item>
      <el-descriptions-item label="学习建议">{{ suggestionText }}</el-descriptions-item>
    </el-descriptions>

    <div v-if="reasoningSteps.length" class="reasoning">
      <div class="field-label">CoT 推理链</div>
      <ol>
        <li v-for="step in reasoningSteps" :key="step">{{ step }}</li>
      </ol>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  error: {
    type: Object,
    required: true,
  },
})

const weakKnowledge = computed(() => {
  const value = props.error.weak_concept_names || props.error.weak_knowledge || props.error.weak_concepts
  if (Array.isArray(value)) return value.filter(Boolean)
  if (typeof value === 'string' && value.trim()) {
    return value.split(/[,，、;；]/).map((item) => item.trim()).filter(Boolean)
  }
  return ['未知知识点']
})

const confidenceText = computed(() => {
  const value = Number(props.error.confidence ?? 0)
  return Number.isFinite(value) ? value.toFixed(2) : '0.00'
})

const conceptRows = computed(() => props.error.concepts || [])
const reasoningSteps = computed(() => props.error.reasoning_steps || [])
const cotStrategy = computed(() => props.error.cot_strategy || {})

const difficultyText = computed(() => {
  const difficulty = props.error.difficulty || cotStrategy.value.difficulty || 'medium'
  const labels = {
    easy: '基础题',
    medium: '中等题',
    hard: '复杂题',
  }
  return labels[difficulty] || '中等题'
})

const suggestionText = computed(() => {
  const suggestion = props.error.learning_suggestion || props.error.suggestion
  if (Array.isArray(suggestion)) return suggestion.join('；')
  return suggestion || '暂无'
})
</script>

<style scoped>
.error-card {
  border-radius: 8px;
  border-color: #e3ecf7;
}

.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.question-id {
  font-weight: 760;
  color: #173454;
  margin-right: 8px;
}

.type-tag {
  vertical-align: middle;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.cot-policy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 14px;
  border-radius: 8px;
  background: #f8fbff;
  border: 1px solid #e4edf7;
  color: #40566f;
}

.cot-policy strong {
  margin-left: 8px;
  color: #173454;
}

.cot-policy span:last-child {
  color: #1769c2;
  font-weight: 700;
  white-space: nowrap;
}

.field-label {
  color: #64758b;
  font-size: 13px;
}

.concept-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.concept-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #e4edf7;
  border-radius: 8px;
  background: #fbfdff;
}

.concept-chip span {
  color: #31465f;
  font-size: 13px;
}

.concept-chip strong {
  color: #1769c2;
}

.analysis-desc {
  --el-descriptions-table-border: 1px solid #e7eef7;
}

.reasoning {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f7fbff;
  border: 1px solid #e4edf7;
}

.reasoning ol {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #2d425c;
  line-height: 1.8;
}
</style>
