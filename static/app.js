const output = document.getElementById("output");
const devLoginBtn = document.getElementById("devLoginBtn");
const loadMeBtn = document.getElementById("loadMeBtn");

function print(value) {
  output.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function devLogin() {
  const payload = {
    telegram_id: Number(document.getElementById("telegramId").value || 100001),
    first_name: document.getElementById("firstName").value || "Dev",
    username: document.getElementById("username").value || "dev_user",
  };

  const res = await fetch("/api/v1/auth/dev", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    print(data);
    return;
  }

  localStorage.setItem("access_token", data.access_token);
  print({ message: "Авторизация успешна", token_preview: `${data.access_token.slice(0, 20)}...` });
}

async function loadMe() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    print("Сначала нажми 'Войти (Dev)'");
    return;
  }

  const res = await fetch("/api/v1/users/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  print(data);
}

devLoginBtn.addEventListener("click", () => {
  devLogin().catch((err) => print(String(err)));
});

loadMeBtn.addEventListener("click", () => {
  loadMe().catch((err) => print(String(err)));
});
