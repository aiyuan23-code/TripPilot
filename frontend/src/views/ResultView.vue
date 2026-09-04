<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import TripMap from '@/components/TripMap.vue'
import { loadTripPlan } from '@/services/planStorage'

const router = useRouter()
const plan = ref(loadTripPlan())

const allAttractions = computed(() =>
  plan.value?.days.flatMap((day) => day.attractions) ?? [],
)

const budgetItems = computed(() => {
  const budget = plan.value?.budget
  if (!budget) return []
  return [
    { label: '景点', value: budget.attraction_cost, icon: '⌖' },
    { label: '住宿', value: budget.hotel_cost, icon: '◇' },
    { label: '餐饮', value: budget.meal_cost, icon: '◌' },
    { label: '交通', value: budget.transportation_cost, icon: '↗' },
  ]
})

function formatMoney(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(`${value}T00:00:00`))
}

function mealLabel(type: string): string {
  return (
    {
      breakfast: '早餐',
      lunch: '午餐',
      dinner: '晚餐',
      snack: '加餐',
      restaurant: '餐饮',
    }[type] || type
  )
}
</script>

<template>
  <section v-if="plan" class="result-page page-wrap">
    <div class="result-hero">
      <div>
        <span class="eyebrow">YOUR TRIP, CURATED</span>
        <h1>{{ plan.city }}，{{ plan.days.length }} 日漫游</h1>
        <p>{{ plan.start_date }} — {{ plan.end_date }}</p>
      </div>
      <button class="secondary-action" @click="router.push('/')">重新规划</button>
    </div>

    <section v-if="plan.budget" class="section-block budget-section">
      <div class="section-title">
        <div><span>01</span><h2>预算概览</h2></div>
        <strong>{{ formatMoney(plan.budget.total) }}</strong>
      </div>
      <div class="budget-grid">
        <article v-for="item in budgetItems" :key="item.label" class="budget-card">
          <span>{{ item.icon }}</span>
          <small>{{ item.label }}</small>
          <strong>{{ formatMoney(item.value) }}</strong>
        </article>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">
        <div><span>02</span><h2>天气速览</h2></div>
      </div>
      <div class="weather-strip">
        <article v-for="weather in plan.weather_info" :key="weather.date">
          <small>{{ formatDate(weather.date) }}</small>
          <strong>{{ weather.day_weather }}</strong>
          <span>{{ weather.night_temp ?? '–' }}° / {{ weather.day_temp ?? '–' }}°</span>
          <em>{{ weather.wind_direction || '风向未知' }}风 {{ weather.wind_power || '–' }}级</em>
        </article>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">
        <div><span>03</span><h2>行程地图</h2></div>
        <small>{{ allAttractions.length }} 个游览地点</small>
      </div>
      <TripMap :attractions="allAttractions" />
    </section>

    <section class="section-block">
      <div class="section-title">
        <div><span>04</span><h2>每日行程</h2></div>
      </div>

      <div class="days-list">
        <article v-for="day in plan.days" :key="day.date" class="day-card">
          <div class="day-index">
            <small>DAY</small>
            <strong>{{ String(day.day_index).padStart(2, '0') }}</strong>
          </div>
          <div class="day-content">
            <div class="day-heading">
              <div>
                <span>{{ formatDate(day.date) }}</span>
                <h3>{{ day.title || `第 ${day.day_index} 天` }}</h3>
              </div>
              <strong>{{ formatMoney(day.estimated_daily_cost) }}</strong>
            </div>
            <p class="day-description">{{ day.description }}</p>

            <div class="itinerary-list">
              <div
                v-for="(attraction, index) in day.attractions"
                :key="attraction.poi_id || attraction.name"
                class="itinerary-item"
              >
                <span class="timeline-dot">{{ index + 1 }}</span>
                <div>
                  <h4>{{ attraction.name }}</h4>
                  <p>{{ attraction.address || '地址待确认' }}</p>
                  <small>
                    建议游览 {{ attraction.visit_duration }} 分钟
                    · 门票 {{ formatMoney(attraction.ticket_price) }}
                    <template v-if="attraction.rating"> · {{ attraction.rating }} 分</template>
                  </small>
                </div>
              </div>
            </div>

            <div class="day-details-grid">
              <div class="detail-box">
                <span>餐饮安排</span>
                <ul>
                  <li v-for="meal in day.meals" :key="`${meal.meal_type}-${meal.name}`">
                    <strong>{{ mealLabel(meal.meal_type) }}</strong>
                    {{ meal.name }} · {{ formatMoney(meal.estimated_cost) }}
                  </li>
                </ul>
              </div>
              <div class="detail-box">
                <span>住宿与交通</span>
                <p v-if="day.hotel">
                  {{ day.hotel.name }} · {{ formatMoney(day.hotel.estimated_cost_per_night) }}/晚
                </p>
                <p v-else>当日不安排住宿</p>
                <small>{{ day.accommodation }}</small>
                <small>交通方式：{{ day.transportation }}</small>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="suggestion-card">
      <span>TRIP NOTES</span>
      <h2>出发前建议</h2>
      <p>{{ plan.overall_suggestions }}</p>
    </section>
  </section>

  <section v-else class="empty-page page-wrap">
    <span>没有找到旅行计划</span>
    <h1>先生成一份属于你的行程吧。</h1>
    <button class="primary-action" @click="router.push('/')">返回规划页面</button>
  </section>
</template>

