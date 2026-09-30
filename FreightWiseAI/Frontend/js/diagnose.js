// Connection check: tests files, Live Server, backend, CORS and model, then names the FIRST failure.
const out = document.getElementById("out");
let firstFail = null;
function section(t) { const h = document.createElement("h2"); h.textContent = t; out.append(h); }
function row(state, title, detail, hint) {
  const r = document.createElement("div"); r.className = "row " + state;
  const tag = document.createElement("span"); tag.className = "tag"; tag.textContent = state === "pass" ? "PASS" : state === "fail" ? "FAIL" : "WARN";
  const body = document.createElement("div"); body.textContent = title + (detail ? ": " + detail : ""); r.append(tag, body); out.append(r);
  if (state === "fail" && !firstFail) firstFail = { title, hint };
}
async function get(path, opts = {}) { return fetch(path, { cache: "no-store", ...opts }); }

(async () => {
  // 1. How was this page opened?
  section("1. How the page was opened");
  if (location.protocol === "file:") row("fail", "Opened as a local file", location.href, "Do not double-click the HTML file. In VS Code right-click login.html and choose 'Open with Live Server'.");
  else row("pass", "Served over HTTP", location.origin);
  if (location.protocol !== "file:" && !["5500"].includes(location.port)) row("warn", "Live Server port is " + (location.port || "default"), "The backend only allows port 5500 unless CORS_ORIGINS is set.");
  row(typeof Chart === "undefined" ? "fail" : "pass", "Chart.js library", typeof Chart === "undefined" ? "did not load" : "loaded", "Chart.js comes from cdnjs.cloudflare.com. Check your internet connection and disable ad blockers for this page.");
  const signed = sessionStorage.getItem("fw_session");
  row(signed ? "pass" : "warn", "Signed in", signed ? JSON.parse(signed).email : "no session in this tab (pages redirect to login)");

  // 2. Files present and current
  section("2. Project files");
  let apiBase = null;
  const need = { "js/api.js": "API_BASE", "js/common.js": "Model Insights", "js/dashboard.js": "renderCards", "js/forecast.js": "save: true", "js/market.js": "drawIndicator",
    "js/history.js": "forecast-history", "js/model.js": "impChart", "js/context.js": "context-status", "css/common.css": ".sidebar", "css/dashboard.css": ".tbl-wrap",
    "dashboard.html": "js/api.js", "forecast.html": "js/api.js", "market.html": "js/api.js", "history.html": "js/api.js", "model.html": "js/api.js", "port.html": "js/context.js", "vessels.html": "js/context.js", "about.html": "About FreightWise AI" };
  for (const [path, marker] of Object.entries(need)) {
    try {
      const r = await get(path);
      if (!r.ok) { row("fail", path, "HTTP " + r.status + " (missing)", "Copy " + path + " into the Frontend folder, in the same subfolder."); continue; }
      const text = await r.text();
      if (path === "js/api.js") { const m = text.match(/API_BASE\s*=\s*"([^"]+)"/); apiBase = m && m[1]; }
      row(text.includes(marker) ? "pass" : "fail", path, text.includes(marker) ? "" : "found, but it is an OLD version", "Replace " + path + " with the latest version.");
    } catch { row("fail", path, "could not be read", "Copy " + path + " into the Frontend folder."); }
  }

  // 3. Backend
  section("3. Backend at " + (apiBase || "(API_BASE not found in js/api.js)"));
  if (!apiBase) row("fail", "API address", "not found", "Replace js/api.js with the latest version.");
  else {
    try {   // is the thing answering on this address really the FreightWise backend?
      const r = await get(apiBase + "/"); let j = null; try { j = await r.json(); } catch {}
      if (j && j.app === "FreightWise AI API") row("pass", "GET /", "FreightWise backend identified");
      else row("fail", "GET /", `HTTP ${r.status}, this is NOT the FreightWise backend`,
        "Another program (often an old backend) is using this port. In PowerShell run: netstat -ano | findstr :5000  then  taskkill /PID <last number> /F  then start python app.py again from the backend folder in the zip.");
    } catch { /* unreachable: reported by the endpoint tests below */ }
    const tests = [["GET", "/api/health"], ["GET", "/api/latest"], ["GET", "/api/history?range=90d"], ["GET", "/api/market?range=90d"], ["GET", "/api/metrics"],
      ["GET", "/api/model-info"], ["GET", "/api/features"], ["GET", "/api/forecast-history"], ["GET", "/api/context-status"], ["POST", "/api/forecast"]];
    for (const [method, path] of tests) {
      const label = method + " " + path;
      try {
        const r = await get(apiBase + path, method === "POST" ? { method, headers: { "Content-Type": "application/json" }, body: "{}" } : {});
        let j = null; try { j = await r.json(); } catch {}
        if (!r.ok || (j && j.success === false)) row("fail", label, "HTTP " + r.status + (j && j.error ? " - " + j.error : ""), "The backend answered with an error. Read the backend terminal for the reason.");
        else if (path === "/api/health") row(j.model_loaded ? "pass" : "fail", label, `model_loaded=${j.model_loaded}, rows=${j.rows}` + (j.detail ? ", " + j.detail : ""), "The model or dataset failed to load. Run 'python check_model.py' in the backend folder.");
        else if (path === "/api/forecast") row("pass", label, "prediction " + Number(j.forecast.value).toFixed(4));
        else row("pass", label, "HTTP " + r.status);
      } catch {
        let cors = false; try { await fetch(apiBase + "/api/health", { mode: "no-cors" }); cors = true; } catch {}
        row("fail", label, cors ? "blocked by CORS" : "no response (backend not reachable)",
          cors ? "The backend runs but rejects this page's address. Open the site from Live Server on port 5500, or set CORS_ORIGINS to " + location.origin + " before 'python app.py'."
               : "The backend is not running or not on that address. Start it: cd backend, activate the venv, python app.py.");
        if (path === "/api/health") break;                     // no point testing the rest
      }
    }
  }

  const s = document.getElementById("summary");
  s.textContent = "";
  if (!firstFail) s.textContent = "All checks passed. The frontend and backend are connected. If a page still looks empty, hard-refresh it with Ctrl+F5 and check the Console (F12) for red errors.";
  else { const b = document.createElement("b"); b.textContent = "First problem: " + firstFail.title; s.append(b, document.createElement("br"), "Fix: " + firstFail.hint); }
})();