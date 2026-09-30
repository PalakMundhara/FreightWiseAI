// FreightWise AI - registration (PROTOTYPE ONLY)
// Accounts are saved in this browser's localStorage. Later this becomes POST /api/register.
const form = document.getElementById("registerForm");
const msg = document.getElementById("formMsg");

// Show / hide password (works for both password fields)
document.querySelectorAll(".eye").forEach(btn => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    const hide = input.type === "password";
    input.type = hide ? "text" : "password";
    btn.classList.toggle("shown", hide);
  });
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  msg.style.color = "#ff9a9a";

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim().toLowerCase();
  const password = document.getElementById("password").value;
  const confirm = document.getElementById("confirm").value;

  if (!name || !email || !password || !confirm) { msg.textContent = "Please fill in all fields."; return; }
  if (!/^\S+@\S+\.\S+$/.test(email)) { msg.textContent = "Enter a valid email address."; return; }
  if (password.length < 8) { msg.textContent = "Password must be at least 8 characters."; return; }
  if (password !== confirm) { msg.textContent = "Passwords do not match."; return; }

  const users = JSON.parse(localStorage.getItem("fw_users") || "[]");
  if (users.some(u => u.email === email)) { msg.textContent = "An account with this email already exists."; return; }

  users.push({ name, email, password });
  localStorage.setItem("fw_users", JSON.stringify(users));
  window.location.href = "login.html?registered=1";
});
