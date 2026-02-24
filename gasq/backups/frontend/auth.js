// admin/auth.js
const AUTH = {
  apiBase() {
    const el = document.getElementById("apiBase");
    return (el ? el.value : "http://localhost:8000").replace(/\/+$/, "");
  },

  get token() {
    return localStorage.getItem("gasq_token") || "";
  },

  set token(v) {
    if (!v) localStorage.removeItem("gasq_token");
    else localStorage.setItem("gasq_token", v);
  },

  async api(path, opts = {}) {
    const base = this.apiBase();
    const headers = Object.assign({}, opts.headers || {});
    if (this.token) headers["Authorization"] = "Bearer " + this.token;
    const res = await fetch(base + path, { ...opts, headers });

    // если токен протух/невалиден — выкидываем на login
    if (res.status === 401) {
      this.token = "";
      if (!location.pathname.endsWith("/admin/login.html")) {
        location.href = "/admin/login.html";
      }
      throw new Error("Not authenticated");
    }

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || ("HTTP " + res.status));
    }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json();
    return res.text();
  },

  async login(username, password) {
    const base = this.apiBase();
    const res = await fetch(base + "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      throw new Error("Неверный логин/пароль");
    }
    const data = await res.json();
    this.token = data.access_token;
    return data;
  },

  logout() {
    this.token = "";
    location.href = "/admin/login.html";
  },

  async me() {
    return this.api("/api/auth/me");
  },

  async requireRole(...roles) {
    const me = await this.me();
    if (roles.length && !roles.includes(me.role)) {
      // если роль не подходит — перекидываем на главную админки
      location.href = "/admin/index.html";
      throw new Error("Forbidden for role: " + me.role);
    }
    return me;
  }
};
