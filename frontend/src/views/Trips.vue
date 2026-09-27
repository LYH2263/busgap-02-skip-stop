<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const savingId = ref<number | null>(null)

async function loadEvents() {
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } catch { events.value = [] }
}

onMounted(async () => {
  trips.value = await api('/trips')
  await loadEvents()
})

async function toggleSkip(trip: any, stop: string, checked: boolean) {
  const next = new Set(trip.skip_stops || [])
  if (checked) next.add(stop); else next.delete(stop)
  // 按站点顺序回写
  const ordered = (trip.stops || []).filter((s: string) => next.has(s))
  savingId.value = trip.id
  try {
    const res = await api(`/trips/${trip.id}/skip-stops`, {
      method: 'PUT',
      body: JSON.stringify({ stop_names: ordered }),
    })
    trip.skip_stops = res.skip_stops || []
    await loadEvents()
  } finally {
    savingId.value = null
  }
}

function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
</script>
<template>
  <h1>班次 · 间隔条带</h1>
  <p class="sub">左侧班次清单（勾选站名即登记越站不停），右侧串车/间隔竖直条带</p>
  <div class="bg-split">
    <aside class="bg-trip-col">
      <h2>班次列表</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">线路 {{ r.line_id }} · 车 {{ r.vehicle_no }}</div>
          <div class="bg-skip-list">
            <label v-for="s in r.stops" :key="s" class="bg-skip-item" :title="`勾选表示 ${r.trip_no} 在「${s}」越站不停`">
              <input
                type="checkbox"
                :checked="(r.skip_stops || []).includes(s)"
                :disabled="savingId === r.id"
                @change="toggleSkip(r, s, ($event.target as HTMLInputElement).checked)"
              />
              <span>{{ s }}</span>
            </label>
          </div>
        </div>
        <div class="bg-trip-meta">{{ r.planned_depart }}</div>
      </div>
    </aside>
    <div class="bg-strip-col">
      <article
        v-for="(e, i) in events"
        :key="i"
        class="bg-gap-strip"
        :class="stripClass(e.status)"
      >
        <header>{{ e.stop_name }}</header>
        <div class="bg-gap-body">
          <div class="bg-gap-val">{{ e.gap_min }}′</div>
          <div>计划 {{ e.planned_headway_min }}′</div>
          <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
          <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : e.status === 'large_gap' ? 'badge-warn' : 'badge-ok'">
            {{ label(e.status) }}
          </span>
        </div>
      </article>
      <p v-if="!events.length" class="muted">暂无间隔事件</p>
    </div>
  </div>
</template>
