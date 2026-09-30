// FreightWise AI - login logic (PROTOTYPE ONLY)
// Accounts live in this browser's localStorage. We replace this with the
// Flask /api/login endpoint later. Never store real passwords like this in production.

const form = document.getElementById("loginForm");
const emailEl = document.getElementById("email");
const pwEl = document.getElementById("password");
const rememberEl = document.getElementById("remember");
const msgEl = document.getElementById("formMsg");
const toggleBtn = document.getElementById("togglePw");

// Show / hide password
toggleBtn.addEventListener("click", () => {
  const hidden = pwEl.type === "password";
  pwEl.type = hidden ? "text" : "password";
  toggleBtn.classList.toggle("shown", hidden);
  toggleBtn.setAttribute("aria-label", hidden ? "Hide password" : "Show password");
});

// Remember me: pre-fill the saved email
const savedEmail = localStorage.getItem("fw_remember_email");
if (savedEmail) { emailEl.value = savedEmail; rememberEl.checked = true; }

document.getElementById("forgot").addEventListener("click", (e) => {
  e.preventDefault();
  msgEl.style.color = "#AFC3D0";
  msgEl.textContent = "Password reset is not available in this prototype.";
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  msgEl.style.color = "#ff8a8a";

  const email = emailEl.value.trim().toLowerCase();
  const password = pwEl.value;

  if (!email || !password) { msgEl.textContent = "Enter your email and password."; return; }
  if (!/^\S+@\S+\.\S+$/.test(email)) { msgEl.textContent = "Enter a valid email address."; return; }

  const users = JSON.parse(localStorage.getItem("fw_users") || "[]");
  const user = users.find(u => u.email === email && u.password === password);

  if (!user) { msgEl.textContent = "Email or password is incorrect."; return; }

  if (rememberEl.checked) localStorage.setItem("fw_remember_email", email);
  else localStorage.removeItem("fw_remember_email");

  sessionStorage.setItem("fw_session", JSON.stringify({ name: user.name, email: user.email }));
  window.location.href = "dashboard.html";
});

// Message shown after registering
if (new URLSearchParams(location.search).get("registered")) {
  msgEl.style.color = "#7be0ff";
  msgEl.textContent = "Account created. Please sign in.";
}
