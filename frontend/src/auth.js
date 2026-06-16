// Estado de autenticação (token JWT no localStorage) + eventos.
import { api } from "./api";

const TOKEN_KEY = "carprice.token";
const USER_KEY = "carprice.user";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const isLogged = () => !!getToken();

let _user = (() => { try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; } })();
export const getUser = () => _user;

function aplica(token, user) {
  if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user)); else localStorage.removeItem(USER_KEY);
  _user = user || null;
  window.dispatchEvent(new Event("auth-mudou"));
}

export async function entrar(email, senha) {
  const r = await api.login(email, senha);
  aplica(r.token, r.user);
  return r.user;
}
export async function cadastrar(nome, email, senha) {
  const r = await api.register(nome, email, senha);
  aplica(r.token, r.user);
  return r.user;
}
export function sair() { aplica(null, null); }

// valida o token no load (se expirou, desloga)
export async function revalidar() {
  if (!getToken()) return;
  try {
    const u = await api.me();
    aplica(getToken(), u);
  } catch {
    aplica(null, null);
  }
}
