// FreightWise AI - shared API helper. Every page talks to the backend through api().
// Dynamic API Base:
// - window.BACKEND_API_URL or localStorage 'freightwise_backend_url' if custom backend is set
// - http://127.0.0.1:5000 when running locally on localhost or 127.0.0.1
// - Relative path "" when hosted on cloud/Vercel
const getApiBase = () => {
  if (typeof window !== "undefined") {
    if (window.BACKEND_API_URL) return window.BACKEND_API_URL;
    try {
      const stored = localStorage.getItem("freightwise_backend_url");
      if (stored) return stored;
    } catch { /* ignore */ }
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.protocol === "file:") {
      return "http://127.0.0.1:5000";
    }
  }
  return "";
};
const API_BASE = getApiBase();

class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(API_BASE + path, { headers: { "Content-Type": "application/json" }, ...options });
  } catch {
    throw new ApiError("FreightWise backend is currently unavailable. Start it with: python app.py", 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* not JSON */ }
  if (data === null) {   // a reply came back, but it was not JSON: some other program is answering on this address
    throw new ApiError(`The server at ${API_BASE} replied (HTTP ${res.status}) but it is not the FreightWise backend. ` +
      "An old backend or another program may be using this port. Run diagnose.html for the fix.", res.status);
  }
  if (!res.ok || data.success === false) throw new ApiError(data.error || "Unable to retrieve freight data.", res.status);
  return data;
}

const isNum = v => typeof v === "number" && Number.isFinite(v);
const fmt = (v, d = 2) => isNum(v) ? v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : "Data unavailable";
const fmtPct = v => isNum(v) ? `${v > 0 ? "+" : ""}${v.toFixed(2)}%` : "Data unavailable";
const $ = id => document.getElementById(id);
const setText = (id, t) => { $(id).textContent = t; };
const trendClass = v => !isNum(v) ? "" : (v > 0 ? "up" : v < 0 ? "down" : "");

function showBanner(msg) {
  const b = $("banner"); b.textContent = msg + " "; b.hidden = false;
  const r = document.createElement("button"); r.textContent = "Retry"; r.onclick = () => location.reload(); b.append(r);
}

// Shared Chart.js look (dark theme)
function chartDefaults() {
  Chart.defaults.color = "#AFC3D0";
  Chart.defaults.font.family = '"Segoe UI", system-ui, sans-serif';
  Chart.defaults.borderColor = "rgba(50,200,255,.10)";
}
// History line + dashed forecast segment. `h` = /api/history response, `fc` = forecast object or null.
function buildFreightChart(canvasId, h, fc, existing) {
  chartDefaults();
  const labels = [...h.dates], n = labels.length;
  const pad = a => (fc ? [...a, null] : a);
  const datasets = [
    { label: "Freight (BDRY close)", data: pad(h.close), borderColor: "#24C6FF", backgroundColor: "rgba(36,198,255,.12)", borderWidth: 2, pointRadius: 0, tension: .25, fill: true },
    { label: "7-day average", data: pad(h.avg_7d), borderColor: "#168BFF", borderWidth: 1.4, pointRadius: 0, tension: .25 },
    { label: "30-day average", data: pad(h.avg_30d), borderColor: "#8aa4b6", borderWidth: 1.4, pointRadius: 0, tension: .25 },
  ];
  if (fc) {
    labels.push(`${fc.approx_target_date} (forecast)`);
    const seg = Array(n + 1).fill(null); seg[n - 1] = h.close[n - 1]; seg[n] = fc.value;
    datasets.push({ label: `Forecast (${fc.horizon})`, data: seg, borderColor: "#ffb84d", borderDash: [7, 5], borderWidth: 2.4,
                    pointRadius: seg.map((_, i) => i === n ? 6 : 0), pointBackgroundColor: "#ffb84d", tension: 0 });
  }
  if (existing) existing.destroy();
  return new Chart($(canvasId), { type: "line", data: { labels, datasets },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      scales: { x: { ticks: { maxTicksLimit: 8, maxRotation: 0 }, title: { display: true, text: "Date" } },
                y: { title: { display: true, text: "BDRY close" } } },
      plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: c => c.parsed.y == null ? null : `${c.dataset.label}: ${fmt(c.parsed.y)}` } } } } });
}

// Generic line/bar chart. extra: {type:"bar", indexAxis:"y"}
function lineChart(id, labels, sets, existing, yTitle, extra = {}) {
  chartDefaults(); if (existing) existing.destroy();
  return new Chart($(id), { type: extra.type || "line", data: { labels, datasets: sets },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: extra.indexAxis || "x", interaction: { mode: "index", intersect: false },
      scales: { x: { ticks: { maxTicksLimit: 8 } }, y: { title: { display: !!yTitle, text: yTitle || "" } } }, plugins: { legend: { position: "bottom" } } } });
}
const SRC = "Source: backend dataset (master_training_dataset_clean.csv)";