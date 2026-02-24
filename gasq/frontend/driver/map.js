// frontend/driver/map.js
// GasQ — Driver Map (super safe)

let map = null;
let markersLayer = null;
let selectedMarker = null;

function byId(id) {
  return document.getElementById(id);
}

function apiBase() {
  const el = byId("apiBase");
  const v = el && el.value ? el.value : "http://127.0.0.1:8000";
  return String(v).trim().replace(/\/+$/, "");
}

function initMap() {
  const el = byId("map");
  if (!el) return;

  // защита от двойной инициализации
  if (window.__gasqMapInited) return;
  window.__gasqMapInited = true;

  // защита: если Leaflet уже привязал контейнер
  if (el._leaflet_id) return;

  map = L.map("map").setView([39.6542, 66.9597], 12);
  markersLayer = L.layerGroup().addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap",
  }).addTo(map);

  loadStations();
}
window.initMap = initMap;

async function loadStations() {
  try {
    const url = apiBase() + "/api/stations/stations";
    const res = await fetch(url);
    if (!res.ok) throw new Error("Stations HTTP " + res.status);

    const stations = await res.json();
    if (!Array.isArray(stations)) throw new Error("Stations response is not array");

    markersLayer.clearLayers();

    for (let i = 0; i < stations.length; i++) {
      addStationMarker(stations[i]);
    }

    setTimeout(function () {
      if (map) map.invalidateSize();
    }, 200);
  } catch (err) {
    console.error("[GasQ Map] loadStations error:", err);
    if (window.toast) window.toast("Ошибка карты", err.message || "loadStations failed");
  }
}

function addStationMarker(st) {
  const lat = Number(st.latitude);
  const lon = Number(st.longitude);
  if (!isFinite(lat) || !isFinite(lon)) return;

  const marker = L.marker([lat, lon]).addTo(markersLayer);

  marker.on("click", function () {
    if (selectedMarker) selectedMarker.setOpacity(1);
    selectedMarker = marker;
    marker.setOpacity(0.6);

    // выбрать АЗС -> проставить stationId
    const input = byId("stationId");
    if (input) input.value = String(st.id);

    if (window.toast) window.toast("АЗС выбрана", String(st.name || "АЗС"));
  });

  const title = String(st.name || "АЗС");
  const addr = String(st.address || "");
  marker.bindPopup("<b>" + title + "</b><br>" + addr);
}