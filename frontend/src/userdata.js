// Roteia carros salvos e histórico: SERVIDOR quando logado, localStorage quando convidado.
import { api } from "./api";
import { isLogged } from "./auth";
import * as local from "./storage";

let _salvas = new Set(); // cache de URLs salvas (modo logado), p/ o ⭐ síncrono

// chamado ao logar / no boot — preenche o cache de salvos do servidor
export async function carregarSalvos() {
  if (!isLogged()) { _salvas = new Set(); return; }
  try {
    const lista = await api.savedList();
    _salvas = new Set(lista.map((s) => s.url));
  } catch { _salvas = new Set(); }
  window.dispatchEvent(new Event("salvos-mudou"));
}

export function estaSalvo(url) {
  return isLogged() ? _salvas.has(url) : local.estaSalvo(url);
}

export async function alternarSalvo(carro) {
  if (isLogged()) {
    if (_salvas.has(carro.url)) { await api.savedRemove(carro.url); _salvas.delete(carro.url); }
    else { await api.savedAdd(carro.url, carro); _salvas.add(carro.url); }
    window.dispatchEvent(new Event("salvos-mudou"));
    return _salvas.has(carro.url);
  }
  return local.alternarSalvo(carro);
}

export async function listarSalvos() {
  if (isLogged()) {
    try { return (await api.savedList()).map((s) => ({ url: s.url, ...s.dados_json })); }
    catch { return []; }
  }
  return local.lerSalvos();
}
export async function removerSalvo(url) {
  if (isLogged()) { await api.savedRemove(url).catch(() => {}); _salvas.delete(url); }
  else local.removerSalvo(url);
}

export async function registrarBusca(criterios, total, filtro) {
  if (isLogged()) {
    await api.historyAdd(criterios, filtro || {}, total, local.rotuloCriterios(criterios)).catch(() => {});
  } else {
    local.registrarBusca(criterios, total, filtro);
  }
}
export async function listarHistorico() {
  if (isLogged()) {
    try {
      return (await api.historyList()).map((h) => ({
        id: String(h.id), ts: Date.parse(h.criado_em), criterios: h.criterios_json,
        filtro: h.filtro_json, label: h.label, total: h.total,
      }));
    } catch { return []; }
  }
  return local.lerHistorico();
}
export async function removerDoHistorico(id) {
  if (isLogged()) await api.historyRemove(id).catch(() => {});
  else local.removerDoHistorico(id);
}
export async function limparHistorico() {
  if (isLogged()) await api.historyClear().catch(() => {});
  else local.limparHistorico();
}
