// Freight Forecast Center: Interactive User Input Engine & Automated Audit
let historyChart = null, compareChart = null, features = [], metrics = null;
let currentBasePrice = 16.14, currentBaselinePred = 15.46;

// 1. Sync Sliders and Inputs
const priceRange = $("inputCloseRange");
const priceNum = $("inputClose");
if (priceRange && priceNum) {
  priceRange.addEventListener("input", e => {
    priceNum.value = parseFloat(e.target.value).toFixed(2);
  });
  priceNum.addEventListener("input", e => {
    if (e.target.value) priceRange.value = e.target.value;
  });
}

const momRange = $("inputMomentumRange");
const momVal = $("inputMomentumVal");
if (momRange && momVal) {
  momRange.addEventListener("input", e => {
    const v = parseFloat(e.target.value);
    momVal.textContent = (v > 0 ? "+" : "") + v.toFixed(1) + "%";
  });
}

// 2. Preset Buttons
$("pillBaseline").addEventListener("click", () => {
  priceNum.value = currentBasePrice.toFixed(2);
  priceRange.value = currentBasePrice.toFixed(2);
  $("inputVolume").value = 150000;
  $("inputRange").value = 0.85;
  $("inputCoal").value = 19.69;
  $("inputPower").value = 135.20;
  $("inputCement").value = 110.00;
  momRange.value = 0;
  momVal.textContent = "0.0%";
  triggerCustomCalculation();
});

$("pillBullish").addEventListener("click", () => {
  const p = (currentBasePrice * 1.15).toFixed(2);
  priceNum.value = p;
  priceRange.value = p;
  $("inputVolume").value = 280000;
  $("inputRange").value = 1.35;
  $("inputCoal").value = 23.50;
  $("inputPower").value = 145.00;
  $("inputCement").value = 118.00;
  momRange.value = 5.0;
  momVal.textContent = "+5.0%";
  triggerCustomCalculation();
});

$("pillBearish").addEventListener("click", () => {
  const p = (currentBasePrice * 0.85).toFixed(2);
  priceNum.value = p;
  priceRange.value = p;
  $("inputVolume").value = 95000;
  $("inputRange").value = 0.55;
  $("inputCoal").value = 16.20;
  $("inputPower").value = 120.00;
  $("inputCement").value = 98.00;
  momRange.value = -4.5;
  momVal.textContent = "-4.5%";
  triggerCustomCalculation();
});

$("pillMonsoon").addEventListener("click", () => {
  priceNum.value = currentBasePrice.toFixed(2);
  priceRange.value = currentBasePrice.toFixed(2);
  $("inputVolume").value = 120000;
  $("inputRange").value = 1.85;
  $("inputCoal").value = 17.50;
  $("inputPower").value = 140.00;
  $("inputCement").value = 105.00;
  momRange.value = 2.0;
  momVal.textContent = "+2.0%";
  triggerCustomCalculation();
});

$("btnResetInputs").addEventListener("click", () => {
  $("pillBaseline").click();
});

// 3. Render Comparison Chart
function renderComparisonChart(inputBase, predValue, baselinePred) {
  chartDefaults();
  const ctx = $("userCompareChart");
  if (!ctx) return;
  if (compareChart) compareChart.destroy();

  const isUp = predValue >= inputBase;
  const labels = ["Your Input Benchmark", "Baseline Reference (t+14)", "Your Custom Forecast (t+14)"];
  const data = [inputBase, baselinePred, predValue];

  compareChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Freight Rate ($)",
        data,
        backgroundColor: [
          "rgba(175, 195, 208, 0.45)",
          "rgba(36, 198, 255, 0.55)",
          isUp ? "rgba(75, 227, 160, 0.75)" : "rgba(255, 138, 138, 0.75)"
        ],
        borderColor: [
          "#AFC3D0",
          "#24C6FF",
          isUp ? "#4be3a0" : "#ff8a8a"
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          title: { display: true, text: "BDRY Price ($)" },
          ticks: { callback: v => "$" + Number(v).toFixed(2) }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => `${c.dataset.label}: $${fmt(c.parsed.y)}`
          }
        }
      }
    }
  });
}

// 4. Update UI with Prediction Results
function updateResultsUI(fc, model) {
  const spread = fc.tree_spread || {};
  setText("userPredPrice", "$" + fmt(fc.value));
  setText("userInputRate", "$" + fmt(fc.input_base_price));

  const delta = fc.absolute_change || 0;
  setText("userDollarDelta", `${delta >= 0 ? "+" : ""}$${fmt(delta)}`);

  setText("userTreeSpread", `$${fmt(spread.p10)} – $${fmt(spread.p90)}`);
  setText("userBaselineRef", "$" + fmt(fc.baseline_model_prediction));

  const badge = $("userTrendBadge");
  badge.className = "trend-indicator " + (fc.trend || "stable");
  const arrow = fc.trend === "up" ? "▲ +" : fc.trend === "down" ? "▼ " : "■ ";
  badge.textContent = `${arrow}${fmtPct(fc.change_percent)}`;

  setText("userRecText", fc.recommendation || "Maintain standard risk protocols across chartering fixtures.");
  renderComparisonChart(fc.input_base_price, fc.value, fc.baseline_model_prediction);
}

// 5. Submit Custom Forecast
async function triggerCustomCalculation() {
  const btn = $("btnRunUserForecast");
  btn.disabled = true;
  $("userForecastStatus").innerHTML = '<span class="spinner"></span>Passing customized figures into 300 Extra Trees estimators…';

  const payload = {
    freight_close: parseFloat($("inputClose").value),
    freight_volume: parseFloat($("inputVolume").value),
    daily_range: parseFloat($("inputRange").value),
    coal_import: parseFloat($("inputCoal").value),
    electricity_demand: parseFloat($("inputPower").value),
    cement_prod: parseFloat($("inputCement").value),
    momentum_pct: parseFloat($("inputMomentumRange").value),
    save: $("checkSaveHistory").checked
  };

  try {
    const res = await api("/api/custom-forecast", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    updateResultsUI(res.forecast, res.model);
    setText("userForecastStatus", "Forecast updated successfully!" + (res.saved ? " Saved to History database." : ""));
  } catch (err) {
    setText("userForecastStatus", "Failed generating forecast: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

$("userInputForecastForm").addEventListener("submit", e => {
  e.preventDefault();
  triggerCustomCalculation();
});

// 6. Automated Pipeline Audit (Secondary Section)
async function loadBaselineAndFeatures() {
  try {
    const [latest, featData] = await Promise.all([
      api("/api/latest").catch(() => null),
      api("/api/features").catch(() => null)
    ]);

    if (latest && isNum(latest.close)) {
      currentBasePrice = latest.close;
      priceNum.value = currentBasePrice.toFixed(2);
      priceRange.value = currentBasePrice.toFixed(2);
      if (latest.forecast && isNum(latest.forecast.value)) {
        currentBaselinePred = latest.forecast.value;
      }
    }

    if (featData) {
      features = featData.features || [];
      setText("asOf", featData.as_of_date || "latest available");
      const list = $("featureList");
      if (list) {
        list.innerHTML = features.slice(0, 15).map(f => `
          <div class="r"><span>${f.name}</span><b>${fmt(f.value, 4)}</b></div>
        `).join("");
      }
    }

    // Run initial calculation with live baseline values
    triggerCustomCalculation();

  } catch (e) {
    showBanner("Connection issue: " + e.message);
  }
}

// Button for secondary section
if ($("genBtn")) {
  $("genBtn").addEventListener("click", async () => {
    $("genBtn").disabled = true;
    $("status").innerHTML = '<span class="spinner"></span>Re-computing automated feed…';
    try {
      const [r, h] = await Promise.all([
        api("/api/forecast", { method: "POST", body: JSON.stringify({ save: true }) }),
        api("/api/history?range=6m")
      ]);
      historyChart = buildFreightChart("fcChart", h, r.forecast, historyChart);
      setText("status", "Automated baseline recomputed.");
    } catch (err) {
      setText("status", "Error: " + err.message);
    } finally {
      $("genBtn").disabled = false;
    }
  });
}

// Start on load
loadBaselineAndFeatures();
