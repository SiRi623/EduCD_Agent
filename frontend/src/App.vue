<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">
        <div class="brand-mark">EA</div>
        <div>
          <div class="brand-title">EduCD-Agent 智慧教育认知诊断智能体</div>
          <div class="brand-subtitle">认知诊断 · 错因分析 · 学情报告 · 教学干预</div>
        </div>
      </div>
      <el-menu
        class="nav-menu"
        mode="horizontal"
        :ellipsis="false"
        :default-active="route.path"
        router
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/student">学生诊断</el-menu-item>
        <el-menu-item index="/teacher">教师看板</el-menu-item>
      </el-menu>
    </el-header>

    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
