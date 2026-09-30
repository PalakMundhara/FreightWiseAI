// Market Intelligence: all figures come from /api/latest, /api/history, /api/market, and /api/live/freight-benchmarks.
let fChart = null, iChart = null, indicators = [];

function drawIndicator() {
  const ind = indicators.find(i => i.column === $("indSel").value);
  if (!ind) return;
  iChart = lineChart("indChart", ind.dates, [{ label: ind.column, data: ind.series, borderColor: "#24C6FF", borderWidth: 2, pointRadius: 0, stepped: true }], iChart, "Value (unit not documented)");
  setText("indNote", `${SRC.replace("Source: ", "Source: ")}. Updates about monthly and is carried forward between updates. Latest ${fmt(ind.latest)}, ${isNum(ind.change_percent) ? fmtPct(ind.change_percent) + " vs previous reading" : "no earlier reading"}.`);
}

function insight(box, sev, title, text) {
  const row = document.createElement("div");
  row.className = "insight";
  const c = document.createElement("span");
  c.className = "chip " + sev;
  c.textContent = sev;
  const b = document.createElement("div"), t = document.createElement("b"), s = document.createElement("span");
  t.textContent = title;
  s.textContent = text;
  b.append(t, s);
  row.append(c, b);
  box.append(row);
}

async function load(range) {
  try {
    const [l, h, m, fLive] = await Promise.all([
      api("/api/latest"),
      api(`/api/history?range=${range}`),
      api(`/api/market?range=${range}`),
      api("/api/live/freight-benchmarks").catch(() => null)
    ]);

    // Live Baltic Benchmarks (OilPriceAPI)
    if (fLive && fLive.freight) {
      const fr = fLive.freight;
      if (fr.bdi !== null) {
        setText("valBDI", fmt(fr.bdi, 1));
        const delta = fr.bdi_change_24h;
        setText("subBDI", `${delta !== null ? fmtPct(delta) + " (24h change)" : "Latest Assessment"} · OilPriceAPI`);
      }
      if (fr.bci !== null) {
        setText("valBCI", fmt(fr.bci, 1));
        const delta = fr.bci_change_24h;
        setText("subBCI", `${delta !== null ? fmtPct(delta) + " (24h change)" : "Latest Assessment"} · OilPriceAPI`);
      }
    }

    setText("mClose", fmt(l.close));
    setText("mCloseSub", `${l.date} · ${fmtPct(l.day_change_percent)} vs previous day`);
    setText("m7", fmt(l.avg_7d));
    setText("m30", fmt(l.avg_30d));

    const c = l.coal_import;
    setText("mCoal", fmt(c.value));
    setText("mCoalSub", `${c.column} · ${isNum(c.change_percent) ? fmtPct(c.change_percent) + " vs previous reading" : "no earlier reading"}`);
    setText("src", SRC + ". " + m.update_note);

    if (!h.count) {
      setText("insights", "No historical freight data available for this period.");
      return;
    }

    fChart = buildFreightChart("freightChart", h, null, fChart);
    indicators = m.indicators;
    const sel = $("indSel"), keep = sel.value;
    sel.textContent = "";
    indicators.forEach(i => {
      const o = document.createElement("option");
      o.value = i.column;
      o.textContent = i.column;
      sel.append(o);
    });

    sel.value = indicators.some(i => i.column === keep) ? keep : (indicators.find(i => i.column === "COL.HRD.IMP.TOT.DOC") || indicators[0]).column;
    drawIndicator();

    const box = $("insights");
    box.textContent = "";
    const first = h.close[0], last = h.close.at(-1), per = (last / first - 1) * 100;
    insight(box, Math.abs(per) >= 15 ? "Watch" : "Information", "Freight over selected period", `Freight moved ${fmtPct(per)} from ${h.dates[0]} (${fmt(first)}) to ${h.dates.at(-1)} (${fmt(last)}).`);
    const d7 = (l.close / l.avg_7d - 1) * 100;
    insight(box, "Information", "Versus recent average", `The latest close is ${fmt(Math.abs(d7))}% ${d7 >= 0 ? "above" : "below"} its 7-day average and ${fmt(Math.abs((l.close / l.avg_30d - 1) * 100))}% ${l.close >= l.avg_30d ? "above" : "below"} its 30-day average.`);
    if (isNum(c.change_percent)) insight(box, "Information", "Import activity", `${c.column} ${c.change_percent >= 0 ? "increased" : "decreased"} ${fmt(Math.abs(c.change_percent))}% compared with its previous reading.`);

  } catch (e) {
    showBanner(e.message);
  }
}

$("indSel").addEventListener("change", drawIndicator);
$("ranges").addEventListener("click", e => {
  const r = e.target.dataset.r;
  if (!r) return;
  document.querySelectorAll("#ranges button").forEach(b => b.classList.toggle("active", b === e.target));
  load(r);
});

load("1y");
