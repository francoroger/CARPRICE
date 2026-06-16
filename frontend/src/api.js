// Cliente da API.
// - Dev: VITE_API_URL vazio → caminho relativo /api (proxy do Vite → backend:8000).
// - Produção (Netlify): VITE_API_URL = URL do backend (Render) → chamada DIRETA
//   (evita o timeout do proxy do Netlify nas buscas longas).
const BASE = import.meta.env.VITE_API_URL || "";

async function req(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = localStorage.getItem("carprice.token");
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(BASE + path, { ...opts, headers });
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch { /* sem corpo */ }
    throw new Error(typeof msg === "string" ? msg : `erro ${r.status}`);
  }
  return r.status === 204 ? null : r.json();
}

export const api = {
  listMonitors: () => req("/api/monitors"),
  createMonitor: (data) => req("/api/monitors", { method: "POST", body: JSON.stringify(data) }),
  updateMonitor: (id, data) => req(`/api/monitors/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteMonitor: (id) => req(`/api/monitors/${id}`, { method: "DELETE" }),

  search: (criterios) => req("/api/search", { method: "POST", body: JSON.stringify(criterios) }),

  scrapeLogs: () => req("/api/scrape-logs"),
  runScrape: () => req("/api/scrape/run", { method: "POST" }),
  scrapeStatus: () => req("/api/scrape/status"),

  fipeMarcas: () => req("/api/fipe/marcas"),
  fipeModelos: (marca) => req(`/api/fipe/modelos?marca=${encodeURIComponent(marca)}`),
  fipeVersoes: (marca, modelo) =>
    req(`/api/fipe/versoes?marca=${encodeURIComponent(marca)}&modelo=${encodeURIComponent(modelo)}`),

  estados: () => req("/api/localidades/estados"),
  municipios: (uf) => req(`/api/localidades/municipios?uf=${encodeURIComponent(uf)}`),

  // auth
  register: (nome, email, senha) => req("/api/auth/register", { method: "POST", body: JSON.stringify({ nome, email, senha }) }),
  login: (email, senha) => req("/api/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),
  me: () => req("/api/auth/me"),
  updateMe: (data) => req("/api/auth/me", { method: "PATCH", body: JSON.stringify(data) }),
  alerts: () => req("/api/account/alerts"),
  // conta (carros salvos + histórico) — exigem login
  savedList: () => req("/api/account/saved"),
  savedAdd: (url, dados) => req("/api/account/saved", { method: "POST", body: JSON.stringify({ url, dados }) }),
  savedRemove: (url) => req(`/api/account/saved?url=${encodeURIComponent(url)}`, { method: "DELETE" }),
  historyList: () => req("/api/account/history"),
  historyAdd: (criterios, filtro, total, label) => req("/api/account/history", { method: "POST", body: JSON.stringify({ criterios, filtro, total, label }) }),
  historyRemove: (id) => req(`/api/account/history/${id}`, { method: "DELETE" }),
  historyClear: () => req("/api/account/history", { method: "DELETE" }),

  portals: () => req("/api/settings/portals"),
  togglePortal: (slug, ativo) => req(`/api/settings/portals/${slug}?ativo=${ativo}`, { method: "PATCH" }),
  scoreParams: () => req("/api/settings/score"),
  saveScore: (valor_json) => req("/api/settings/score", { method: "PUT", body: JSON.stringify({ valor_json }) }),
};
