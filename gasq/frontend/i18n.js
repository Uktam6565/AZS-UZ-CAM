(function () {
  const LANG_KEY = "gasq_lang";

  const dict = {
    ru: {
      // Common
      lang: "Язык",
      none: "—",
      loading: "Загрузка…",
      created: "Создан",
      called: "Вызван",
      done: "Завершён",
      status: "Статус",
      refresh: "Обновить",
      reset: "Сбросить",
      waiting: "Ожидает",
      fueling: "Заправка",
      cancelled: "Отменён",

      install_app: "📲 Установить приложение",
      install_not_ready:
        "Установка сейчас недоступна. Откройте сайт в Chrome/Edge через localhost или https.",
      installed_ok: "✅ Приложение установлено",

      // Driver
      driver_title: "Водитель",
      get_ticket: "Получить талон",
      my_ticket: "Мой талон",

      // Operator
      operator_title: "Оператор",
      operator_sub: "Вызов → заправка → завершение + история",
      back_admin: "⬅ Админка",
      board: "🖥 Табло",
      logout: "Выйти",

      station_id: "Station ID",
      fuel_filter: "Тип топлива (фильтр)",
      fuel_all: "Все",
      api: "API",
      auto_refresh: "Автообновление",

      call_next: "📣 Вызвать следующего",
      start_fueling: "⛽ Начать заправку",
      finish: "✅ Завершить",
      cancel: "✖ Отменить",

      auth_label: "Авторизация:",
      auth_ok: "OK",
      auth_no_token: "нет токена",

      check_in: "Check-in",
      scan_start: "Сканировать",
      scan_stop: "Стоп",
      check_in_btn: "Check-in",
      auto_checkin: "Авто-check-in после скана",
      camera: "Камера",

      now_serving: "Сейчас обслуживается",
      no_active: "нет активного",
      operator_hint: "Если нет активного талона — сначала нажми «Вызвать следующего».",
      waiting_list: "Ожидают (до 20)",
      no_waiting: "Нет ожидающих",

      history_title: "📚 История талонов",
      history_refresh: "📚 Обновить историю",
      history_press: "Нажми “Обновить историю”",
      history_statuses: "Статусы:",
      history_empty: "Пусто за выбранный период",

      from: "С",
      to: "По",
      all: "Все",
      limit: "Лимит",

      // Terminal (если нужно)
      terminal_title: "🖥 GasQ — Табло",
      terminal_sub: "Показывает вызванные талоны",
      called_list: "Вызваны (до 10)",
      waiting_count: "Ожидают",
      updated_at: "Обновлено",
    },

    uz: {
      lang: "Til",
      none: "—",
      loading: "Yuklanmoqda…",
      created: "Yaratildi",
      called: "Chaqirildi",
      done: "Yakunlandi",
      status: "Holat",
      refresh: "Yangilash",
      reset: "Tozalash",
      waiting: "Kutilmoqda",
      fueling: "Yoqilg‘i quyilmoqda",
      cancelled: "Bekor qilindi",

      install_app: "📲 Ilovani o‘rnatish",
      install_not_ready:
        "Hozir o‘rnatib bo‘lmaydi. Chrome/Edge’da localhost yoki https orqali oching.",
      installed_ok: "✅ Ilova o‘rnatildi",

      driver_title: "Haydovchi",
      get_ticket: "Navbat olish",
      my_ticket: "Mening talonim",

      operator_title: "Operator",
      operator_sub: "Chaqirish → yoqilg‘i → yakunlash + tarix",
      back_admin: "⬅ Admin",
      board: "🖥 Tablo",
      logout: "Chiqish",

      station_id: "Station ID",
      fuel_filter: "Yoqilg‘i turi (filtr)",
      fuel_all: "Barchasi",
      api: "API",
      auto_refresh: "Avto-yangilash",

      call_next: "📣 Keyingisini chaqirish",
      start_fueling: "⛽ Yoqilg‘ini boshlash",
      finish: "✅ Yakunlash",
      cancel: "✖ Bekor qilish",

      auth_label: "Avtorizatsiya:",
      auth_ok: "OK",
      auth_no_token: "token yo‘q",

      check_in: "Check-in",
      scan_start: "Skan qilish",
      scan_stop: "To‘xtatish",
      check_in_btn: "Check-in",
      auto_checkin: "Skan’dan so‘ng auto-check-in",
      camera: "Kamera",

      now_serving: "Hozir xizmatda",
      no_active: "faol emas",
      operator_hint: "Agar faol talon bo‘lmasa — avval «Keyingisini chaqirish»ni bosing.",
      waiting_list: "Kutilmoqda (20 gacha)",
      no_waiting: "Kutilayotgan yo‘q",

      history_title: "📚 Talonlar tarixi",
      history_refresh: "📚 Tarixni yangilash",
      history_press: "“Tarixni yangilash”ni bosing",
      history_statuses: "Holatlar:",
      history_empty: "Tanlangan davrda bo‘sh",

      from: "Dan",
      to: "Gacha",
      all: "Barchasi",
      limit: "Limit",
    },

    en: {
      lang: "Language",
      none: "—",
      loading: "Loading…",
      created: "Created",
      called: "Called",
      done: "Done",
      status: "Status",
      refresh: "Refresh",
      reset: "Reset",
      waiting: "Waiting",
      fueling: "Fueling",
      cancelled: "Cancelled",

      install_app: "📲 Install app",
      install_not_ready:
        "Install is not available now. Open in Chrome/Edge via localhost or https.",
      installed_ok: "✅ App installed",

      driver_title: "Driver",
      get_ticket: "Get ticket",
      my_ticket: "My ticket",

      operator_title: "Operator",
      operator_sub: "Call → fueling → finish + history",
      back_admin: "⬅ Admin",
      board: "🖥 Board",
      logout: "Logout",

      station_id: "Station ID",
      fuel_filter: "Fuel type (filter)",
      fuel_all: "All",
      api: "API",
      auto_refresh: "Auto refresh",

      call_next: "📣 Call next",
      start_fueling: "⛽ Start fueling",
      finish: "✅ Finish",
      cancel: "✖ Cancel",

      auth_label: "Auth:",
      auth_ok: "OK",
      auth_no_token: "no token",

      check_in: "Check-in",
      scan_start: "Scan",
      scan_stop: "Stop",
      check_in_btn: "Check-in",
      auto_checkin: "Auto check-in after scan",
      camera: "Camera",

      now_serving: "Now serving",
      no_active: "no active",
      operator_hint: "If there is no active ticket — press “Call next” first.",
      waiting_list: "Waiting (up to 20)",
      no_waiting: "No waiting tickets",

      history_title: "📚 Ticket history",
      history_refresh: "📚 Refresh history",
      history_press: "Press “Refresh history”",
      history_statuses: "Statuses:",
      history_empty: "No data for selected period",

      from: "From",
      to: "To",
      all: "All",
      limit: "Limit",
    },
  };

  function getLang() {
    return localStorage.getItem(LANG_KEY) || "ru";
  }

  function t(key) {
    const lang = getLang();
    return dict[lang]?.[key] ?? dict["ru"]?.[key] ?? key;
  }

  function applyLang() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (!key) return;
      el.textContent = t(key);
    });

    const docKey = document.documentElement.getAttribute("data-i18n-doc-title");
    if (docKey) document.title = t(docKey);
  }

  function setLang(lang) {
    localStorage.setItem(LANG_KEY, lang);
    applyLang();
    window.dispatchEvent(new Event("gasq:lang-changed"));
  }

  window.I18N = { t, setLang, getLang, applyLang };

  document.addEventListener("DOMContentLoaded", applyLang);
})();
