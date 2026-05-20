import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import StudentDiagnosis from '../views/StudentDiagnosis.vue'
import TeacherDashboard from '../views/TeacherDashboard.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/student', name: 'StudentDiagnosis', component: StudentDiagnosis },
  { path: '/teacher', name: 'TeacherDashboard', component: TeacherDashboard },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
