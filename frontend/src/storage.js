// Persistência local (sobrevive a refresh E a redeploys do backend).
// Sem login: os dados ficam no navegador do usuário.

const K = {
  busca: "carprice.busca.v1",       // estado da última busca (filtros + resultados)
  historico: "carprice.historico.v1", // buscas recentes (re-executáveis)
  salvos: "carprice.salvos.v1",     // carros favoritados
};

function ler(chave, padrao) {
  try {
    const v = localStorage.getItem(chave);
    return v ? JSON.parse(v) : padrao;
  } catch { return padrao; }
}
function gravar(chave, valor) {
  try { localStorage.setItem(chave, JSON.stringify(valor)); } catch { /* quota/priv */ }
}

// --- estado da Busca (não perde ao atualizar a página) --- //
export const salvarBusca = (estado) => gravar(K.busca, estado);
export const lerBusca = () => ler(K.busca, null);

// --- histórico de buscas (máx 30, mais recente primeiro) --- //
// `filtro` (opcional) é o snapshot do formulário, p/ "Refazer" restaurar os dropdowns.
export function registrarBusca(criterios, total, filtro) {
  const hist = ler(K.historico, []);
  const label = rotuloCriterios(criterios);
  const nova = { id: `${Date.now()}`, ts: Date.now(), criterios, filtro: filtro || null, total, label };
  // dedup: remove entrada idêntica (mesmos critérios) e põe a nova no topo
  const semDup = hist.filter((h) => JSON.stringify(h.criterios) !== JSON.stringify(criterios));
  gravar(K.historico, [nova, ...semDup].slice(0, 30));
}
export const lerHistorico = () => ler(K.historico, []);
export const limparHistorico = () => gravar(K.historico, []);
export function removerDoHistorico(id) {
  gravar(K.historico, ler(K.historico, []).filter((h) => h.id !== id));
}

// --- carros salvos (favoritos) --- //
export const lerSalvos = () => ler(K.salvos, []);
export function estaSalvo(url) {
  return ler(K.salvos, []).some((c) => c.url === url);
}
export function alternarSalvo(carro) {
  const atuais = ler(K.salvos, []);
  const existe = atuais.some((c) => c.url === carro.url);
  const novos = existe
    ? atuais.filter((c) => c.url !== carro.url)
    : [{ ...carro, salvoEm: Date.now() }, ...atuais];
  gravar(K.salvos, novos);
  return !existe; // true = passou a estar salvo
}
export function removerSalvo(url) {
  gravar(K.salvos, ler(K.salvos, []).filter((c) => c.url !== url));
}

// rótulo legível dos critérios (p/ exibir no histórico)
export function rotuloCriterios(c = {}) {
  const p = [];
  if (c.marca) p.push(c.marca);
  if (c.modelo) p.push(c.modelo);
  if (c.versao) p.push(String(c.versao).split(" ").slice(0, 3).join(" "));
  if (c.ano_min || c.ano_max) p.push(`${c.ano_min || ""}${c.ano_max ? "–" + c.ano_max : "+"}`);
  if (c.cidade) p.push(c.cidade);
  else if (c.uf) p.push(c.uf);
  return p.join(" · ") || "Busca geral";
}
