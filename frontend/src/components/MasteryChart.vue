<template>
  <div class="chart-panel panel">
    <div class="chart-title">{{ title }}</div>
    <div v-if="hasData" ref="chartRef" class="chart-box"></div>
    <div v-else class="empty-state">暂无数据</div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  mastery: {
    type: Object,
    default: () => ({}),
  },
  labels: {
    type: Object,
    default: () => ({}),
  },
  title: {
    type: String,
    default: '知识点掌握度',
  },
})

const chartRef = ref(null)
let chart = null

const entries = computed(() => Object.entries(props.mastery || {}))
const hasData = computed(() => entries.value.length > 0)

function renderChart() {
  if (!hasData.value || !chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const ids = entries.value.map(([name]) => name)
  const names = ids.map((id) => props.labels[id] || id)
  const values = entries.value.map(([, value]) => Number(value))
  chart.setOption({
    grid: { left: 48, right: 24, top: 30, bottom: 72 },
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const item = params[0]
        const conceptId = ids[item.dataIndex]
        const title = conceptId === item.name ? item.name : `${item.name}（${conceptId}）`
        return `${title}<br/>掌握度：${Number(item.value).toFixed(2)}`
      },
    },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        interval: 0,
        rotate: names.length > 5 ? 28 : 0,
        color: '#52657d',
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d6e2f0' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      interval: 0.2,
      axisLabel: { color: '#52657d' },
      splitLine: { lineStyle: { color: '#edf3fa' } },
    },
    series: [
      {
        name: '掌握度',
        type: 'bar',
        data: values,
        barMaxWidth: 36,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color(params) {
            const value = params.value
            if (value < 0.6) return '#f56c6c'
            if (value < 0.8) return '#e6a23c'
            return '#2f80ed'
          },
        },
        label: {
          show: true,
          position: 'top',
          color: '#334960',
          formatter: ({ value }) => Number(value).toFixed(2),
        },
      },
    ],
  })
}

function resizeChart() {
  chart?.resize()
}

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', resizeChart)
})

watch(
  () => props.mastery,
  () => nextTick(renderChart),
  { deep: true },
)

watch(
  () => props.labels,
  () => nextTick(renderChart),
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-panel {
  padding: 18px;
}

.chart-title {
  font-size: 18px;
  font-weight: 700;
  color: #132948;
  margin-bottom: 12px;
}

.chart-box {
  width: 100%;
  height: 360px;
}
</style>
