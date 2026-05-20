import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000',
  timeout: 1000000000,
})

export function getApiErrorMessage(error) {
  const message = error?.message || ''
  const code = error?.code || ''

  if (code === 'ECONNABORTED' || message.toLowerCase().includes('timeout')) {
    return 'Qwen 分析时间较长，请稍后重试或先使用缓存/Mock 模式。'
  }

  if (message === 'Network Error') {
    return '后端服务未连接，请先运行 python app.py'
  }

  return error?.response?.data?.message || message || '请求失败，请稍后重试'
}

function unwrap(response) {
  return response.data
}

export function getHealth() {
  return api.get('/api/health').then(unwrap)
}

export function getStudents() {
  return api.get('/api/students').then(unwrap)
}

export function getStudentsDetail() {
  return api.get('/api/students/detail').then(unwrap)
}

export function getQuestions() {
  return api.get('/api/questions').then(unwrap)
}

export function getDiagnose(studentId) {
  return api.get(`/api/diagnose/${studentId}`).then(unwrap)
}

export function getReport(studentId) {
  return api.get(`/api/report/${studentId}`).then(unwrap)
}

export function getFullAnalysis(studentId) {
  return api.get(`/api/full-analysis/${studentId}`).then(unwrap)
}

export function getStudentMemory(studentId) {
  return api.get(`/api/memory/${studentId}`).then(unwrap)
}

export function getClassRecentMemory() {
  return api.get('/api/memory/class/recent').then(unwrap)
}

export function clearMemory() {
  return api.post('/api/memory/clear').then(unwrap)
}

export function getClassSummary() {
  return api.get('/api/class/summary').then(unwrap)
}

export function trainDina() {
  return api.post('/api/train/dina').then(unwrap)
}

export function getDinaParams() {
  return api.get('/api/dina/params').then(unwrap)
}

export function validateDataset() {
  return api.get('/api/dataset/validate').then(unwrap)
}

export function clearCache() {
  return api.get('/api/cache/clear').then(unwrap)
}
