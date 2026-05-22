<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useToolRegistry } from '@/stores/toolRegistry';

const props = defineProps<{
  windowId: string;
  data: Record<string, any>;
}>();

const registry = useToolRegistry();

// ── Reactive state ──
const city = ref('北京');
const latitude = ref(39.9042);
const longitude = ref(116.4074);
const temperature = ref<number | null>(null);
const feelsLike = ref<number | null>(null);
const weatherCode = ref<number | null>(null);
const humidity = ref<number | null>(null);
const windSpeed = ref<number | null>(null);
const aqi = ref<number | null>(null);
const dailyMax = ref<number | null>(null);
const dailyMin = ref<number | null>(null);
const loading = ref(false);
const error = ref('');
const searchQuery = ref('');
const useFahrenheit = ref(false);
const searchResults = ref<Array<{ name: string; lat: number; lon: number; country: string }>>([]);
const searching = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;
const lastFetchKey = ref('');

// ── WMO weather code → emoji + Chinese label ──
const weatherMap: Record<number, { emoji: string; label: string }> = {
  0: { emoji: '☀️', label: '晴' },
  1: { emoji: '🌤', label: '少云' },
  2: { emoji: '⛅', label: '多云' },
  3: { emoji: '☁️', label: '阴' },
  45: { emoji: '🌫', label: '雾' },
  48: { emoji: '🌫', label: '雾凇' },
  51: { emoji: '🌦', label: '小毛毛雨' },
  53: { emoji: '🌦', label: '毛毛雨' },
  55: { emoji: '🌦', label: '大毛毛雨' },
  56: { emoji: '🌧', label: '冻毛毛雨' },
  57: { emoji: '🌧', label: '冻毛毛雨' },
  61: { emoji: '🌧', label: '小雨' },
  63: { emoji: '🌧', label: '中雨' },
  65: { emoji: '🌧', label: '大雨' },
  66: { emoji: '🌧', label: '冻雨' },
  67: { emoji: '🌧', label: '冻雨' },
  71: { emoji: '❄️', label: '小雪' },
  73: { emoji: '❄️', label: '中雪' },
  75: { emoji: '❄️', label: '大雪' },
  77: { emoji: '❄️', label: '雪粒' },
  80: { emoji: '🌦', label: '阵雨' },
  81: { emoji: '🌦', label: '中阵雨' },
  82: { emoji: '🌦', label: '大阵雨' },
  85: { emoji: '❄️', label: '小阵雪' },
  86: { emoji: '❄️', label: '大阵雪' },
  95: { emoji: '⛈', label: '雷暴' },
  96: { emoji: '⛈', label: '雷暴伴冰雹' },
  99: { emoji: '⛈', label: '雷暴伴冰雹' },
};

function getWeatherInfo(code: number | null): { emoji: string; label: string } {
  if (code === null) return { emoji: '—', label: '未知' };
  return weatherMap[code] || { emoji: '🌡', label: '未知' };
}

const weatherInfo = computed(() => getWeatherInfo(weatherCode.value));

// ── Temperature conversion ──
function formatTemp(celsius: number | null): string {
  if (celsius === null) return '—';
  if (useFahrenheit.value) {
    return `${Math.round(celsius * 9 / 5 + 32)}°F`;
  }
  return `${Math.round(celsius)}°C`;
}

// ── AQI labels ──
function getAqiInfo(value: number | null): { emoji: string; label: string } {
  if (value === null) return { emoji: '—', label: '未知' };
  if (value <= 20) return { emoji: '😊', label: '优' };
  if (value <= 40) return { emoji: '🙂', label: '良' };
  if (value <= 60) return { emoji: '😐', label: '轻度污染' };
  if (value <= 80) return { emoji: '😷', label: '中度污染' };
  if (value <= 100) return { emoji: '🤢', label: '重度污染' };
  return { emoji: '💀', label: '严重污染' };
}

const aqiInfo = computed(() => getAqiInfo(aqi.value));

// ── API calls ──
async function fetchWeather(lat: number, lon: number) {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('天气数据获取失败');
  return resp.json();
}

async function fetchAqi(lat: number, lon: number) {
  const url = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=european_aqi`;
  const resp = await fetch(url);
  if (!resp.ok) return null;
  return resp.json();
}

async function refreshWeather() {
  const key = `${latitude.value.toFixed(2)},${longitude.value.toFixed(2)}`;
  if (key === lastFetchKey.value && temperature.value !== null) return;
  lastFetchKey.value = key;

  loading.value = true;
  error.value = '';
  try {
    const [weatherData, aqiData] = await Promise.all([
      fetchWeather(latitude.value, longitude.value),
      fetchAqi(latitude.value, longitude.value),
    ]);
    const cur = weatherData.current;
    temperature.value = cur.temperature_2m;
    feelsLike.value = cur.apparent_temperature;
    weatherCode.value = cur.weather_code;
    humidity.value = cur.relative_humidity_2m;
    windSpeed.value = cur.wind_speed_10m;
    const daily = weatherData.daily;
    if (daily) {
      dailyMax.value = daily.temperature_2m_max[0];
      dailyMin.value = daily.temperature_2m_min[0];
    }
    if (aqiData?.current?.european_aqi != null) {
      aqi.value = aqiData.current.european_aqi;
    }
  } catch (e: any) {
    error.value = e.message || '获取天气失败';
  } finally {
    loading.value = false;
  }
}

async function searchCity(query: string) {
  if (!query.trim()) return;
  searching.value = true;
  searchResults.value = [];
  try {
    const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=5&language=zh&format=json`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('搜索失败');
    const data = await resp.json();
    if (data.results) {
      searchResults.value = data.results.map((r: any) => ({
        name: r.name + (r.admin1 ? `, ${r.admin1}` : '') + (r.country ? `, ${r.country}` : ''),
        lat: r.latitude,
        lon: r.longitude,
        country: r.country || '',
      }));
    }
  } catch (e: any) {
    error.value = e.message || '搜索失败';
  } finally {
    searching.value = false;
  }
}

function selectCity(result: { name: string; lat: number; lon: number }) {
  city.value = result.name.split(',')[0];
  latitude.value = result.lat;
  longitude.value = result.lon;
  searchQuery.value = '';
  searchResults.value = [];
  lastFetchKey.value = '';
  registry.updateToolConfig(props.windowId, { city: city.value, lat: result.lat, lon: result.lon });
  refreshWeather();
}

function doSearch() {
  searchCity(searchQuery.value);
}

// ── Init ──
onMounted(() => {
  if (props.data.city) {
    city.value = props.data.city;
  }
  if (props.data.lat && props.data.lon) {
    latitude.value = props.data.lat;
    longitude.value = props.data.lon;
  }
  if (props.data.useFahrenheit) {
    useFahrenheit.value = props.data.useFahrenheit;
  }
  refreshWeather();

  // Auto-refresh every 5 minutes
  refreshTimer = setInterval(() => {
    lastFetchKey.value = '';
    refreshWeather();
  }, 5 * 60 * 1000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});

// ── Toggle unit and persist ──
function toggleUnit() {
  useFahrenheit.value = !useFahrenheit.value;
  registry.updateToolConfig(props.windowId, {
    city: city.value,
    lat: latitude.value,
    lon: longitude.value,
    useFahrenheit: useFahrenheit.value,
  });
}
</script>

<template>
  <div class="flex flex-col h-full text-sm select-none">
    <!-- Search bar -->
    <div class="relative mb-3">
      <div class="flex gap-2">
        <input
          v-model="searchQuery"
          class="flex-1 px-3 py-1.5 text-sm bg-bg-secondary rounded-[8px] outline-none border border-transparent focus:border-dai text-text-primary placeholder:text-text-secondary/40"
          placeholder="搜索城市..."
          @keydown.enter.prevent="doSearch"
        />
        <button
          class="px-3 py-1.5 text-sm bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors flex-shrink-0 disabled:opacity-50"
          :disabled="searching"
          @click="doSearch"
        >
          {{ searching ? '...' : '搜索' }}
        </button>
      </div>
      <!-- Search results dropdown -->
      <div
        v-if="searchResults.length > 0"
        class="absolute top-full left-0 right-0 mt-1 bg-bg-primary border border-border/60 rounded-[8px] shadow-lg z-10 overflow-hidden"
      >
        <div
          v-for="(r, i) in searchResults"
          :key="i"
          class="px-3 py-2 text-sm text-text-primary hover:bg-bg-secondary cursor-pointer transition-colors truncate"
          @click="selectCity(r)"
        >
          {{ r.name }}
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading && temperature === null" class="flex-1 flex items-center justify-center text-text-secondary/50 text-xs">
      <div class="flex flex-col items-center gap-2">
        <svg class="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32" stroke-linecap="round"/></svg>
        <span>加载中...</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error && temperature === null" class="flex-1 flex items-center justify-center text-error/70 text-xs">
      {{ error }}
    </div>

    <!-- Weather display -->
    <div v-else class="flex-1 flex flex-col gap-2">
      <!-- City name + unit toggle -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1.5 min-w-0">
          <span class="text-sm font-semibold text-text-primary flex-shrink-0">📍</span>
          <span class="text-sm font-semibold text-text-primary truncate min-w-0">{{ city }}</span>
        </div>
        <button
          class="px-2 py-0.5 text-[11px] bg-bg-secondary hover:bg-border text-text-secondary hover:text-text-primary rounded-[6px] transition-colors"
          @click="toggleUnit"
        >
          {{ useFahrenheit ? '°C' : '°F' }}
        </button>
      </div>

      <!-- Main weather: icon + temperature + description -->
      <div class="flex items-center gap-3 px-2 py-3 bg-bg-secondary/50 rounded-[10px]">
        <span class="text-4xl">{{ weatherInfo.emoji }}</span>
        <div class="flex flex-col">
          <span class="text-2xl font-bold text-text-primary">{{ formatTemp(temperature) }}</span>
          <span class="text-[11px] text-text-secondary/60">体感 {{ formatTemp(feelsLike) }}</span>
          <span class="text-[11px] text-text-secondary/70">{{ weatherInfo.label }}</span>
        </div>
        <div class="ml-auto text-right">
          <div class="text-xs text-text-secondary/50">
            <span v-if="dailyMin !== null">↑ {{ formatTemp(dailyMax) }}</span>
            <span v-if="dailyMin !== null" class="ml-1.5">↓ {{ formatTemp(dailyMin) }}</span>
          </div>
        </div>
      </div>

      <!-- Detail grid: humidity, wind, AQI -->
      <div class="grid grid-cols-3 gap-2 mt-1">
        <div class="flex flex-col items-center py-2 px-1 bg-bg-secondary/30 rounded-[8px]">
          <span class="text-[10px] text-text-secondary/50 mb-0.5">💧 湿度</span>
          <span class="text-sm font-medium text-text-primary">{{ humidity !== null ? `${humidity}%` : '—' }}</span>
        </div>
        <div class="flex flex-col items-center py-2 px-1 bg-bg-secondary/30 rounded-[8px]">
          <span class="text-[10px] text-text-secondary/50 mb-0.5">💨 风力</span>
          <span class="text-sm font-medium text-text-primary">{{ windSpeed !== null ? `${windSpeed} km/h` : '—' }}</span>
        </div>
        <div class="flex flex-col items-center py-2 px-1 bg-bg-secondary/30 rounded-[8px]">
          <span class="text-[10px] text-text-secondary/50 mb-0.5">{{ aqiInfo.emoji }} 空气质量</span>
          <span class="text-sm font-medium text-text-primary">{{ aqi !== null ? aqiInfo.label : '—' }}</span>
        </div>
      </div>

      <!-- Refresh hint -->
      <div class="text-[10px] text-text-secondary/30 text-center mt-auto pt-1">
        每5分钟自动刷新 · 数据来源 Open-Meteo
      </div>
    </div>
  </div>
</template>
