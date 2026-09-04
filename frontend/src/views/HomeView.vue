<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { generateTripPlan, getApiErrorMessage } from '@/services/api'
import { saveTripPlan } from '@/services/planStorage'
import type { TripPlanRequest } from '@/types'

const router = useRouter()

function localDate(offsetDays = 0): string {
  const value = new Date()
  value.setDate(value.getDate() + offsetDays)
  const timezoneOffset = value.getTimezoneOffset() * 60_000
  return new Date(value.getTime() - timezoneOffset).toISOString().slice(0, 10)
}

const form = reactive<TripPlanRequest>({
  city: '成都',
  start_date: localDate(),
  end_date: localDate(2),
  preferences: ['历史文化', '美食'],
  budget_level: 'medium',
  transportation: 'public_transport',
  accommodation: 'economy',
})

const preferenceOptions = ['历史文化', '美食', '自然风光', '亲子', '购物', '艺术']
const loading = ref(false)
const progress = ref(0)
const loadingStatus = ref('准备开始规划…')
const errorMessage = ref('')

function togglePreference(preference: string): void {
  const index = form.preferences.indexOf(preference)
  if (index >= 0) form.preferences.splice(index, 1)
  else form.preferences.push(preference)
}

function updateLoadingStatus(): void {
  if (progress.value < 24) loadingStatus.value = '正在搜索适合你的景点…'
  else if (progress.value < 44) loadingStatus.value = '正在查询天气与酒店…'
  else if (progress.value < 64) loadingStatus.value = '正在筛选当地餐厅…'
  else if (progress.value < 82) loadingStatus.value = 'AI 正在编排行程…'
  else loadingStatus.value = '正在补充地点详情并计算预算…'
}

async function submitPlan(): Promise<void> {
  errorMessage.value = ''
  if (!form.city.trim()) {
    errorMessage.value = '请输入目的地城市。'
    return
  }
  if (form.end_date < form.start_date) {
    errorMessage.value = '结束日期不能早于开始日期。'
    return
  }

  loading.value = true
  progress.value = 8
  updateLoadingStatus()
  const timer = window.setInterval(() => {
    if (progress.value < 92) {
      progress.value = Math.min(92, progress.value + 4)
      updateLoadingStatus()
    }
  }, 1_200)

  try {
    const plan = await generateTripPlan({
      ...form,
      city: form.city.trim(),
      preferences: [...form.preferences],
    })
    progress.value = 100
    loadingStatus.value = '旅行计划生成完成！'
    saveTripPlan(plan)
    await router.push({ name: 'result' })
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    window.clearInterval(timer)
    loading.value = false
  }
}
</script>

<template>
  <section class="home-page page-wrap">
    <div class="hero-grid">
      <div class="hero-copy">
        <span class="eyebrow">AI TRAVEL CONCIERGE</span>
        <h1>让每一次出发，<br /><em>都有清晰答案。</em></h1>
        <p>
          告诉我们城市、日期与偏好。TripPilot 将结合真实地点、天气和预算，生成一份可以直接出发的旅行计划。
        </p>
        <div class="feature-row">
          <span>真实 POI</span>
          <span>智能路线</span>
          <span>透明预算</span>
        </div>
      </div>

      <div class="planner-card">
        <div class="card-heading">
          <span>01</span>
          <div>
            <h2>规划你的旅程</h2>
            <p>填写基本需求，剩下的交给 TripPilot</p>
          </div>
        </div>

        <a-alert
          v-if="errorMessage"
          class="form-alert"
          type="error"
          show-icon
          :message="errorMessage"
        />

        <form class="planner-form" @submit.prevent="submitPlan">
          <label class="field field-wide">
            <span>目的地</span>
            <input v-model="form.city" placeholder="例如：成都" autocomplete="off" />
          </label>

          <label class="field">
            <span>出发日期</span>
            <input v-model="form.start_date" type="date" />
          </label>

          <label class="field">
            <span>结束日期</span>
            <input v-model="form.end_date" type="date" :min="form.start_date" />
          </label>

          <div class="field field-wide">
            <span>旅行偏好</span>
            <div class="choice-grid">
              <button
                v-for="preference in preferenceOptions"
                :key="preference"
                type="button"
                class="choice-chip"
                :class="{ active: form.preferences.includes(preference) }"
                @click="togglePreference(preference)"
              >
                {{ preference }}
              </button>
            </div>
          </div>

          <label class="field">
            <span>预算级别</span>
            <select v-model="form.budget_level">
              <option value="low">经济实惠</option>
              <option value="medium">舒适适中</option>
              <option value="high">品质优先</option>
            </select>
          </label>

          <label class="field">
            <span>交通方式</span>
            <select v-model="form.transportation">
              <option value="public_transport">公共交通</option>
              <option value="taxi">出租车 / 网约车</option>
              <option value="driving">自驾</option>
            </select>
          </label>

          <label class="field field-wide">
            <span>住宿类型</span>
            <select v-model="form.accommodation">
              <option value="hostel">青年旅舍</option>
              <option value="economy">经济型酒店</option>
              <option value="mid_range">舒适型酒店</option>
              <option value="boutique">精品酒店</option>
              <option value="luxury">高端酒店</option>
            </select>
          </label>

          <button class="primary-action" type="submit" :disabled="loading">
            <span>{{ loading ? '正在规划' : '开始规划' }}</span>
            <span aria-hidden="true">→</span>
          </button>
        </form>

        <div v-if="loading" class="loading-panel">
          <div class="loading-topline">
            <strong>{{ loadingStatus }}</strong>
            <span>{{ progress }}%</span>
          </div>
          <a-progress
            :percent="progress"
            :show-info="false"
            stroke-color="#e65f3c"
            trail-color="#e8e2d8"
          />
          <p>完整规划通常需要几十秒，请不要关闭页面或重复提交。</p>
        </div>
      </div>
    </div>
  </section>
</template>

