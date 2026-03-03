// frontend/pwa-install.js
(function () {
  function t(key) {
  if (window.I18N && typeof window.I18N.t === "function") {
    return window.I18N.t(key);
  }
  const fallback = {
    install_app: "📲 Установить приложение",
    install_not_ready: "Установка сейчас недоступна. Откройте сайт в Chrome/Edge через localhost или https.",
    installed_ok: "✅ Приложение установлено",
  };
  return fallback[key] || key;
}


  let deferredPrompt = null;

  function isStandalone() {
    const mql =
      window.matchMedia && window.matchMedia("(display-mode: standalone)").matches;
    const ios = window.navigator && window.navigator.standalone === true;
    return !!(mql || ios);
  }

  function ensureButton() {
    const host = document.getElementById("installBox");
    if (!host) return null;

    let btn = document.getElementById("btnInstall");
    if (!btn) {
      btn = document.createElement("button");
      btn.id = "btnInstall";
      btn.className = "btn small good";
      btn.style.display = "none";
      host.appendChild(btn);
    }
    btn.textContent = t("install_app");
    return btn;
  }

  function hide(btn) {
    if (btn) btn.style.display = "none";
  }
  function show(btn) {
    if (btn && !isStandalone()) btn.style.display = "inline-flex";
  }

  function applyText(btn) {
    if (!btn) return;
    btn.textContent = t("install_app");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = ensureButton();
    if (!btn) return;

    if (isStandalone()) hide(btn);

    window.addEventListener("gasq:lang-changed", () => applyText(btn));

    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredPrompt = e;
      show(btn);
      applyText(btn);
    });

    window.addEventListener("appinstalled", () => {
      deferredPrompt = null;
      hide(btn);
      if (typeof window.toast === "function") window.toast(t("installed_ok"));
    });

    btn.addEventListener("click", async () => {
      try {
        if (!deferredPrompt) {
          alert(t("install_not_ready"));
          return;
        }
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
        hide(btn);
      } catch (err) {
        console.error(err);
        alert(t("install_not_ready"));
      }
    });

    applyText(btn);
  });
})();
