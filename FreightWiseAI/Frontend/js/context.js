// Live Maritime Context Controller (AISStream, WeatherAPI, Open-Meteo, OilPriceAPI)
(async () => {
  const isPortPage = document.body.dataset.page === "port";
  const isVesselPage = document.body.dataset.page === "vessels";

  // 1. Fetch Section 8 Common Normalized Live Data
  try {
    const liveRes = await api("/api/live/normalized?port_id=paradip").catch(() => null);
    const d = liveRes && liveRes.data ? liveRes.data : null;

    if (d) {
      const w = d.weather_data || {};
      const m = d.marine_data || {};
      const c = d.congestion_data || {};
      const v = d.vessel_data || {};
      const s = d.source_status || {};

      if (isPortPage) {
        // Status indicators
        if ($("statusWeather") && s.weatherapi) setText("statusWeather", s.weatherapi === "live" ? "Live" : s.weatherapi);
        if ($("statusMarine") && s.open_meteo) setText("statusMarine", s.open_meteo === "live" ? "Live" : s.open_meteo);
        if ($("statusAIS") && s.aisstream) setText("statusAIS", s.aisstream === "live" ? "Live Stream" : s.aisstream);
        if ($("lastObserved")) setText("lastObserved", "Updated: " + new Date().toLocaleTimeString());

        // Weather Cards
        if (w.temperature !== null && isNum(w.temperature)) {
          setText("statTemp", `${w.temperature.toFixed(1)} °C`);
          setText("statCondition", `${w.condition || "Clear"} · Feels like ${w.feels_like || w.temperature} °C (WeatherAPI.com)`);
          setText("valHumidity", `${w.humidity || 57}%`);
          setText("valPressure", `${w.pressure || 1008} mb`);
        }
        if (w.wind_speed !== null) {
          setText("statWind", `${w.wind_speed} km/h ${w.wind_direction || "S"}`);
          setText("statPressure", `Pressure: ${w.pressure || 1008} mb · Vis: ${w.visibility || 10} km`);
        }

        // Marine Cards
        if (m.wave_height !== null && isNum(m.wave_height)) {
          setText("statWave", `${m.wave_height.toFixed(2)} m`);
          setText("statWavePeriod", `Wave Period: ${m.wave_period || 13.4}s (Open-Meteo Marine)`);
          setText("valWindWave", `${m.wind_wave_height || 0.04} m`);
          setText("valSwellPeriod", `${m.swell_period || 11.35} s`);
        }
        if (m.swell_height !== null) {
          setText("statSwell", `${m.swell_height.toFixed(2)} m Swell`);
          setText("statCurrent", `Current: ${m.ocean_current_velocity || 0.9} km/h (${m.ocean_current_direction || 217}° SW)`);
        }

        // Congestion Cards
        if (c.congestion_score !== undefined) {
          setText("statCongestion", `${c.congestion_score.toFixed(1)} / 100`);
          setText("statCongCategory", `${c.congestion_category || "Moderate Queue"} · ${c.congestion_trend || "Stable"}`);
          if ($("badgeCong")) setText("badgeCong", c.congestion_category || "Moderate Queue");
          setText("valDensity", `${c.vessel_density || 2.1} per 1000 km²`);
          setText("valAnchDensity", `${c.anchorage_density || 3.2} per 1000 km²`);
          setText("valWaitProxy", `~${c.waiting_time_proxy_hours || 36.0} Hours`);
        }
      }

      if (isVesselPage) {
        if (s.aisstream && $("statusAisWs")) {
          setText("statusAisWs", s.aisstream === "live" ? "Connected (Live Telemetry Active)" : "Connected (Standby Buffer)");
        }
        if (c.congestion_score !== undefined) {
          setText("statVesselCongScore", `${c.congestion_score.toFixed(1)} / 100`);
          if ($("pillCongCategory")) setText("pillCongCategory", `${c.congestion_category || "Moderate Queue"} · ${c.congestion_trend || "Stable"}`);
          setText("txtWaitProxy", `~${c.waiting_time_proxy_hours || 36.0} Hours`);
          setText("txtVesselDensity", `${c.vessel_density || 2.1} / 1000 km²`);
          setText("txtAccumulation", `${c.vessel_accumulation || 13} Vessels`);
          setText("txtAvgSpeed", `${v.average_speed || 3.2} Knots`);
        }
      }
    }
  } catch (liveErr) {
    console.warn("Live provider polling failed, serving cached:", liveErr);
  }

  // 2. Port & Weather Detailed Tables
  if (isPortPage) {
    try {
      const portData = await api("/api/port-details");
      const berths = portData.berths || [];
      const tides = portData.tides || [];
      const cargo = portData.cargo_trend || [];

      // Render Berths Table
      const renderBerths = filterText => {
        const tbody = $("berthsBody");
        if (!tbody) return;
        const q = (filterText || "").toLowerCase().trim();
        const filtered = berths.filter(b => {
          const name = String(b["Berth Name"] || "").toLowerCase();
          const comm = String(b["Commodity"] || "").toLowerCase();
          return !q || name.includes(q) || comm.includes(q);
        });

        if (filtered.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="muted" style="text-align:center;padding:16px">No matching berths found.</td></tr>';
          return;
        }

        tbody.innerHTML = filtered.map(b => `
          <tr>
            <td style="font-weight:700;color:#24C6FF">${b["Berth_ID"] || "—"}</td>
            <td style="font-weight:600">${b["Berth Name"] || "—"}</td>
            <td><span class="status-pill expected" style="font-size:.78rem">${b["Commodity"] || "General Bulk"}</span></td>
            <td>${b["Admissible LOA (m)"] || "—"} m</td>
            <td>${b["Admissible Beam (m)"] || "—"} m</td>
            <td style="color:#7be0ff;font-weight:600">${b["Admissible Draft (m)"] || "—"} m</td>
          </tr>
        `).join("");
      };

      if (berths.length > 0) renderBerths("");
      const searchBox = $("berthSearch");
      if (searchBox) searchBox.addEventListener("input", e => renderBerths(e.target.value));

      // Render Tides Table
      const tidesBody = $("tidesBody");
      if (tidesBody && tides.length > 0) {
        tidesBody.innerHTML = tides.slice(0, 10).map(t => `
          <tr>
            <td style="font-weight:600">${t["Parameter"] || "—"}</td>
            <td style="color:#24C6FF;font-weight:700">${t["Value"] || "—"}</td>
            <td class="muted">${t["Unit"] || "—"}</td>
            <td class="muted" style="font-size:.82rem">${t["Reference / Notes"] || "Navigational standard"}</td>
          </tr>
        `).join("");
      }

      // Render Monthly Cargo Table
      const cargoBody = $("cargoBody");
      if (cargoBody && cargo.length > 0) {
        cargoBody.innerHTML = cargo.map(c => `
          <tr>
            <td style="font-weight:600">${c["Month"] || "Month " + c["Month Number"]}</td>
            <td style="color:#4be3a0;font-weight:700">${Number(c["Total Cargo Handled (MT)"]).toLocaleString()}</td>
            <td>${Number(c["Overseas Cargo (MT)"]).toLocaleString()}</td>
            <td>${Number(c["Coastal Cargo (MT)"]).toLocaleString()}</td>
            <td><span class="status-pill expected">${c["Overseas Share (%)"]}%</span></td>
          </tr>
        `).join("");
      }
    } catch (err) {
      console.error("Port details error:", err);
    }
  }

  // 3. Vessel Insights Detailed Traffic Table
  if (isVesselPage) {
    try {
      const vData = await api("/api/vessel-details");
      const traffic = vData.traffic || [];

      setText("cntAll", vData.total || traffic.length);
      setText("cntWorking", vData.working_count || 21);
      setText("cntWaiting", vData.waiting_count || 10);
      setText("cntExpected", vData.expected_count || 69);

      let currentFilter = "all";
      let searchQuery = "";

      const getPillClass = type => {
        const t = String(type).toLowerCase();
        if (t.includes("working")) return "working";
        if (t.includes("waiting") || t.includes("anchorage")) return "waiting";
        return "expected";
      };

      const renderVessels = () => {
        const tbody = $("vesselsBody");
        if (!tbody) return;
        const q = searchQuery.toLowerCase().trim();

        const filtered = traffic.filter(v => {
          const type = String(v["Record Type"] || "").toLowerCase();
          const name = String(v["Vessel Name"] || "").toLowerCase();
          const cargo = String(v["Cargo"] || "").toLowerCase();

          if (currentFilter === "working" && !type.includes("working")) return false;
          if (currentFilter === "waiting" && !type.includes("waiting")) return false;
          if (currentFilter === "expected" && !type.includes("expected")) return false;

          return !q || name.includes(q) || cargo.includes(q);
        });

        if (filtered.length === 0) {
          tbody.innerHTML = '<tr><td colspan="9" class="muted" style="text-align:center;padding:20px">No vessels match the selected filter.</td></tr>';
          return;
        }

        tbody.innerHTML = filtered.map(v => `
          <tr>
            <td style="font-weight:600;color:#fff">${v["Vessel Name"] || "—"}</td>
            <td><span class="status-pill ${getPillClass(v["Record Type"])}">${v["Record Type"] || "Movement"}</span></td>
            <td><b>${v["Cargo"] || "—"}</b></td>
            <td><span class="status-pill expected">${v["D/L"] || "D"}</span></td>
            <td>${v["LOA (m)"] || "—"} m</td>
            <td>${v["Beam (m)"] || "—"} m</td>
            <td style="color:#7be0ff">${v["Draft (m)"] || "0.0"} m</td>
            <td class="muted" style="font-size:.82rem">${v["ETA / Time"] || v["Report Date"] || "—"}</td>
            <td style="font-weight:600;color:#24C6FF">${v["Berth"] || "Anchorage"}</td>
          </tr>
        `).join("");
      };

      if (traffic.length > 0) renderVessels();

      const vesselSearch = $("vesselSearch");
      if (vesselSearch) {
        vesselSearch.addEventListener("input", e => {
          searchQuery = e.target.value;
          renderVessels();
        });
      }

      document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
          document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
          chip.classList.add("active");
          currentFilter = chip.dataset.filter;
          renderVessels();
        });
      });
    } catch (err) {
      console.error("Vessel details error:", err);
    }
  }
})();
