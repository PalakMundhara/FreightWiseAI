// FreightWise AI - shared app shell: login guard, sidebar, mobile menu, logout.
// Add <body class="app" data-page="dashboard"> and <script src="js/common.js"> to every inner page.
(function () {
  const session = JSON.parse(sessionStorage.getItem("fw_session") || "null");
  if (!session) { location.replace("login.html"); return; }   // not signed in -> back to login

  const pages = [
    ["dashboard", "Dashboard",           "M3 13h8V3H3zM13 21h8V11h-8zM13 3v6h8V3zM3 21h8v-6H3z"],
    ["forecast",  "Forecast Center",     "M3 17l6-6 4 4 8-8M15 7h6v6"],
    ["market",    "Market Intelligence", "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"],
    ["port",      "Port & Weather",      "M12 5a2 2 0 1 0 0 .01M12 7v13M6 13c0 4 3 7 6 7s6-3 6-7M8 11h8"],
    ["vessels",   "Vessel Insights",     "M3 17l2 3h14l2-3zM6 17V11h12v6M9 11V7h6v4"],
    ["history",   "History",             "M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"],
    ["model",     "Model Insights",      "M4 20V10M10 20V4M16 20v-8M22 20V8"],
    ["about",     "About",               "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v6M12 7.5v.5"],
  ];
  const current = document.body.dataset.page;

  const links = pages.map(([id, label, d]) =>
    `<a href="${id}.html" class="${id === current ? "active" : ""}"><svg viewBox="0 0 24 24"><path d="${d}"/></svg>${label}</a>`
  ).join("");

  document.body.insertAdjacentHTML("afterbegin", `
    <button class="menu-btn" id="menuBtn" aria-label="Open menu">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
    </button>
    <aside class="sidebar" id="sidebar">
      <div class="side-brand">
        <svg viewBox="0 0 146 76"><rect x="60" y="15" width="30" height="10" rx="2" fill="#fff"/><rect x="50" y="25" width="50" height="11" rx="2" fill="#fff"/><rect x="40" y="36" width="70" height="11" rx="2" fill="#fff"/><path d="M22 47 H128 L112 62 H38 Z" fill="#24C6FF"/></svg>
        <div>Freight<span>Wise AI</span></div>
      </div>
      <nav class="nav-links">${links}</nav>
      <div class="side-user">
        <div class="name" id="userName"></div>
        <div class="mail" id="userMail"></div>
        <button class="logout" id="logoutBtn">Log out</button>
      </div>
    </aside>`);

  document.getElementById("userName").textContent = session.name;   // textContent = safe from HTML injection
  document.getElementById("userMail").textContent = session.email;

  const sidebar = document.getElementById("sidebar");
  const closeMenu = () => { sidebar.classList.remove("open"); document.querySelector(".scrim")?.remove(); };
  document.getElementById("menuBtn").addEventListener("click", () => {
    sidebar.classList.add("open");
    const s = document.createElement("div"); s.className = "scrim"; s.addEventListener("click", closeMenu);
    document.body.appendChild(s);
  });
  document.getElementById("logoutBtn").addEventListener("click", () => {
    sessionStorage.removeItem("fw_session");
    location.href = "login.html";
  });
})();
