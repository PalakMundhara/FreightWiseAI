// Model Insights: everything comes from /api/model-info and /api/metrics.
(async () => {
  try {
    const [i, m] = await Promise.all([api("/api/model-info"), api("/api/metrics")]);
    setText("mName", i.model.name); setText("mType", i.model.type); setText("mHor", i.model.horizon); setText("mTarget", i.model.target);
    setText("mFeat", i.model.n_features); setText("mTrees", `${i.model.n_estimators} trees`);
    const p = $("period"); p.textContent = "";
    Object.entries(i.training_period).forEach(([k, [a, b]]) => { const d = document.createElement("div"); d.textContent = `${k[0].toUpperCase() + k.slice(1)}: ${a} to ${b}`; p.append(d); });
    const body = $("metrics");
    [["Extra Trees (this model)", m.model_recomputed], ["Naive \"no change\" baseline", m.naive_persistence_recomputed]].forEach(([n, v]) => {
      const tr = document.createElement("tr"); [n, fmt(v.mae, 3), fmt(v.rmse, 3), fmt(v.smape_percent) + "%"].forEach(x => { const td = document.createElement("td"); td.textContent = x; tr.append(td); }); body.append(tr); });
    setText("mNote", `Recomputed live from the saved model on the out-of-sample test period (${m.test_period[0]} to ${m.test_period[1]}, ${m.n_test} forecasts). ${m.note}`);
    const top = i.feature_importance.slice(0, 15);
    lineChart("impChart", top.map(x => x.feature), [{ label: "Importance", data: top.map(x => x.importance), backgroundColor: "#24C6FF" }], null, "", { type: "bar", indexAxis: "y" });
    setText("impNote", i.note + ` Removed from the final model: ${i.excluded_from_final_model.join(", ")}.`);
  } catch (e) { showBanner(e.message); }
})();
