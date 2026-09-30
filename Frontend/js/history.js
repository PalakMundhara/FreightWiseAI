// History: saved forecasts (SQLite via /api/forecast-history) or out-of-sample test rows (/api/backtest).
let mode = "saved", all = [], shown = [];
const cols = ["date", "input", "predicted", "horizon", "actual", "diff", "pct", "model"];

async function load() {
  setText("hNote", "Loading freight intelligence…"); $("rows").textContent = "";
  try {
    if (mode === "saved") {
      const r = await api("/api/forecast-history");
      all = r.rows.map(x => ({ date: x.as_of_date, input: x.input_freight, predicted: x.predicted, horizon: x.horizon, actual: x.actual, diff: x.difference, pct: x.percent_error, model: x.model }));
    } else {
      const r = await api("/api/backtest?limit=1000");
      all = r.rows.map(x => ({ date: x.date, input: x.input_freight, predicted: x.predicted, horizon: x.horizon, actual: x.actual, diff: x.error, pct: x.percent_error, model: x.model }));
    }
    const hs = [...new Set(all.map(r => r.horizon))], sel = $("hSel"); sel.length = 1;
    hs.forEach(h => { const o = document.createElement("option"); o.value = h; o.textContent = h; sel.append(o); });
    render();
  } catch (e) { showBanner(e.message); setText("hNote", ""); }
}
function render() {
  const q = $("q").value.toLowerCase(), f = $("dFrom").value, t = $("dTo").value, h = $("hSel").value;
  shown = all.filter(r => (!q || Object.values(r).join(" ").toLowerCase().includes(q)) && (!f || r.date >= f) && (!t || r.date <= t) && (!h || r.horizon === h));
  const body = $("rows"); body.textContent = "";
  shown.forEach(r => { const tr = document.createElement("tr");
    [r.date, fmt(r.input), fmt(r.predicted), r.horizon, isNum(r.actual) ? fmt(r.actual) : "Pending", isNum(r.diff) ? fmt(r.diff) : "Pending", isNum(r.pct) ? fmtPct(r.pct) : "Pending", r.model]
      .forEach(v => { const td = document.createElement("td"); td.textContent = v; tr.append(td); }); body.append(tr); });
  setText("hNote", !all.length ? (mode === "saved" ? "No saved forecasts yet. Generate one in the Forecast Center." : "No data available.")
    : !shown.length ? "No rows match the current filters."
    : `${shown.length} of ${all.length} rows. ` + (mode === "saved" ? "\"Pending\" means the real value 14 trading observations later is not in the dataset yet." : "Out-of-sample period: the model did not see these rows in training."));
}
$("tabs").addEventListener("click", e => { const m = e.target.dataset.m; if (!m) return; mode = m;
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("active", b === e.target)); load(); });
["q", "dFrom", "dTo", "hSel"].forEach(id => $(id).addEventListener("input", render));
$("exportBtn").addEventListener("click", () => {
  if (!shown.length) { setText("hNote", "Nothing to export."); return; }
  const head = ["Date", "Input freight", "Predicted", "Horizon", "Actual", "Difference", "Percent error", "Model"];
  const csv = [head, ...shown.map(r => cols.map(c => r[c] ?? "Pending"))].map(r => r.join(",")).join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = `freightwise_${mode}_history.csv`; a.click();
});
load();