// Cliente da API.
// - Dev: VITE_API_URL vazio → caminho relativo /api (proxy do Vite → backend:8000).
// - Produção (Netlify): VITE_API_URL = URL do backend (Render) → chamada DIRETA
//   (evita o timeout do proxy do Netlify nas buscas longas).
const BASE = import.meta.env.VITE_API_URL || "";

async function req(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
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

  portals: () => req("/api/settings/portals"),
  togglePortal: (slug, ativo) => req(`/api/settings/portals/${slug}?ativo=${ativo}`, { method: "PATCH" }),
  scoreParams: () => req("/api/settings/score"),
  saveScore: (valor_json) => req("/api/settings/score", { method: "PUT", body: JSON.stringify({ valor_json }) }),
};
