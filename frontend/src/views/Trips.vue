<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const trips = ref<any[]>([])
const arrivals = ref<any[]>([])
const events = ref<any[]>([])
const stops = ref<string[]>([])
const savingId = ref<number | null>(null)

async function refreshEvents() {
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } catch { events.value = [] }
}

onMounted(async () => {
  const [t, a] = await Promise.all([api('/trips'), api('/arrivals')])
  trips.value = t
  arrivals.value = a
  const seqOf: Record<string, number> = {}
  for (const r of a) {
    if (seqOf[r.stop_name] === undefined || r.stop_seq < seqOf[r.stop_name]) seqOf[r.stop_name] = r.stop_seq
  }
  // 越站后该站可能没有任何到站，仍需从班次的越站标记里补回站名
  for (const tr of t) {
    for (const s of (tr.skipped_stops || [])) {
      if (seqOf[s] === undefined) seqOf[s] = Number.MAX_SAFE_INTEGER
    }
  }
  stops.value = Object.keys(seqOf).sort((x, y) => seqOf[x] - seqOf[y])
  await refreshEvents()
})

function isSkipped(r: any, stop: string) {
  return (r.skipped_stops || []).includes(stop)
}

async function toggleSkip(r: any, stop: string) {
  const next = new Set<string>(r.skipped_stops || [])
  if (next.has(stop)) next.delete(stop); else next.add(stop)
  const payload = [...next]
  r.skipped_stops = payload
  savingId.value = r.id
  try {
    const saved = await api(`/trips/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({ skipped_stops: payload }),
    })
    r.skipped_stops = saved.skipped_stops || []
    await refreshEvents()
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
  <p class="sub">左侧班次清单，勾选站名即登记越站不停；右侧串车/间隔竖直条带</p>
  <div class="bg-split">
    <aside class="bg-trip-col">
      <h2>班次列表（勾选越站）</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row" :class="{ 'row-saving': savingId === r.id }">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">线路 {{ r.line_id }} · 车 {{ r.vehicle_no }}</div>
          <div class="skip-boxes">
            <span class="skip-label">越站：</span>
            <label v-for="s in stops" :key="s" class="skip-chip" :class="{ on: isSkipped(r, s) }">
              <input type="checkbox" :checked="isSkipped(r, s)" @change="toggleSkip(r, s)" />
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
<style scoped>
.skip-boxes { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; margin-top: 0.4rem; }
.skip-label { color: var(--bg-dim); font-size: 0.72rem; }
.skip-chip {
  display: inline-flex; align-items: center; gap: 0.2rem;
  font-size: 0.72rem; padding: 0.1rem 0.35rem;
  border: 1px solid var(--bg-edge); color: var(--bg-dim);
  cursor: pointer; user-select: none;
}
.skip-chip input { accent-color: var(--bg-red); margin: 0; cursor: pointer; }
.skip-chip.on { border-color: var(--bg-red); color: var(--bg-red); background: rgba(255,77,109,0.12); }
.row-saving { opacity: 0.6; }
</style>
