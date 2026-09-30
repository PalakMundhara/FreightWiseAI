// Dashboard: every number comes from the Flask API (no placeholder values).
let chart = null, latest = null, forecast = null, metrics = null;

const WATCH_PCT = 5, ATTENTION_PCT = 15;
const severity = p => Math.abs(p) >= ATTENTION_PCT ? "Attention" : Math.abs(p) >= WATCH_PCT ? "Watch" : "Information";
const dir = (p, up, down) => p >= 0 ? up : down;

function renderCards() {
  setText("cClose", fmt(latest.close));
  setText("cCloseSub", `${latest.date} · ${fmtPct(latest.day_change_percent)} vs previous day`);
  setText("c7", fmt(latest.avg_7d));
  setText("c30", fmt(latest.avg_30d));
  const c = latest.coal_import;
  setText("cCoal", fmt(c.value));
  setText("cCoalSub", `${c.column} · ${isNum(c.change_percent) ? fmtPct(c.change_percent) + " vs previous reading" : "no earlier reading"} · unit not documented`);
  if (forecast) {
    setText("cFc", fmt(forecast.value));
    setText("cFcSub", `${forecast.horizon} · ≈ ${forecast.approx_target_date}`);
    setText("cChg", fmtPct(forecast.change_percent));
    $("cChg").className = "value " + trendClass(forecast.change_percent);
    setText("cChgSub", `Trend: ${forecast.trend}`);
  } else {
    ["cFc", "cChg"].forEach(id => setText(id, "Data unavailable"));
    setText("cFcSub", "Forecast model unavailable");
  }
}

function buildInsights() {
  const out = [];
  if (forecast) {
    const p = forecast.change_percent;
    out.push({ sev: severity(p), title: "Forecast change", text: `The model's ${forecast.horizon} forecast (${fmt(forecast.value)}) is ${fmt(Math.abs(p))}% ${dir(p, "above", "below")} the latest close (${fmt(latest.close)}).` });
  }
  const p30 = (latest.close / latest.avg_30d - 1) * 100;
  out.push({ sev: severity(p30), title: "Freight trend", text: `The latest close is ${fmt(Math.abs(p30))}% ${dir(p30, "above", "below")} its 30-day average.` });
  const p7 = (latest.avg_7d / latest.avg_30d - 1) * 100;
  out.push({ sev: severity(p7), title: "Short vs longer trend", text: `The 7-day average is ${fmt(Math.abs(p7))}% ${dir(p7, "above", "below")} the 30-day average.` });
  const c = latest.coal_import;
  if (isNum(c.change_percent)) {
    out.push({ sev: severity(c.change_percent), title: "Import activity", text: `${c.column} ${dir(c.change_percent, "increased", "decreased")} ${fmt(Math.abs(c.change_percent))}% versus its previous reading (updates about monthly).` });
  }
  if (metrics) {
    const m = metrics.model_recomputed.mae, n = metrics.naive_persistence_recomputed.mae;
    out.push({ sev: m > n ? "Watch" : "Information", title: "Model reliability",
      text: `On the out-of-sample test period (${metrics.test_period[0]} to ${metrics.test_period[1]}) the model's mean absolute error was ${fmt(m)} versus ${fmt(n)} for a simple "no change" baseline. ` +
            (m > n ? "The baseline was more accurate, so treat the forecast as one input among several." : "The model was more accurate than the baseline.") });
  }
  out.push({ sev: "Information", title: "Decision support", text: "Consider the forecast alongside procurement timing, vessel availability and market conditions." });
  return out;
}

function renderInsights() {
  const box = $("insights"); box.textContent = "";
  buildInsights().forEach(i => {
    const row = document.createElement("div"); row.className = "insight";
    const chip = document.createElement("span"); chip.className = "chip " + i.sev; chip.textContent = i.sev;
    const body = document.createElement("div");
    const b = document.createElement("b"); b.textContent = i.title;
    const t = document.createElement("span"); t.textContent = i.text;
    body.append(b, t); row.append(chip, body); box.append(row);
  });
}

async function loadChart(range) {
  try {
    const h = await api(`/api/history?range=${range}`);
    if (!h.count) { $("chartNote").textContent = "No historical data available for this period."; return; }
    chart = buildFreightChart("mainChart", h, forecast, chart);
    $("chartNote").textContent = `Source: backend dataset (${h.count} points).` + (forecast ? " The dashed line is the model's t+14 forecast." : "");
  } catch (e) { showBanner(e.message); }
}

async function init() {
  setText("today", new Date().toLocaleDateString(undefined, { dateStyle: "long" }));
  try {
    latest = (await api("/api/latest"));
    [forecast, metrics] = await Promise.all([
      api("/api/forecast", { method: "POST", body: "{}" }).then(r => r.forecast).catch(() => null),
      api("/api/metrics").catch(() => null),
    ]);
    renderCards();
    renderInsights();
    await loadChart("1y");

    // Fetch live feeds for ticker
    api("/api/live/normalized?port_id=paradip").then(res => {
      if (res && res.data) {
        const d = res.data;
        const w = d.weather_data || {}, m = d.marine_data || {}, c = d.congestion_data || {}, f = d.freight_data || {};
        if (w.temperature !== null) setText("tickWeather", `${w.temperature.toFixed(1)} °C ${w.condition || "Clear"} (Wind ${w.wind_speed || 8} kph ${w.wind_direction || "S"})`);
        if (m.wave_height !== null) setText("tickMarine", `${m.wave_height.toFixed(2)}m Waves (Swell ${m.swell_height || 0.98}m)`);
        if (c.congestion_score !== undefined) setText("tickCong", `Score ${c.congestion_score.toFixed(1)}/100 (${c.congestion_category || "Moderate"})`);
        if (f.bdi !== null) setText("tickBDI", `${fmt(f.bdi, 1)} (${fmtPct(f.bdi_change_24h)})`);
        if (f.bci !== null) setText("tickBCI", `${fmt(f.bci, 1)} (${fmtPct(f.bci_change_24h)})`);
      }
    }).catch(() => null);

  } catch (e) {
    showBanner(e.message);
    document.querySelectorAll(".stat .value").forEach(el => el.textContent = "Data unavailable");
    $("insights").textContent = "Unable to retrieve freight data.";
  }
}

$("ranges").addEventListener("click", e => {
  const r = e.target.dataset.r; if (!r) return;
  document.querySelectorAll("#ranges button").forEach(b => b.classList.toggle("active", b === e.target));
  loadChart(r);
});

init();
