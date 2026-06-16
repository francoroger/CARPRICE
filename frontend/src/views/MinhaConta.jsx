import { useState } from "react";
import { api } from "../api";
import { getUser, sair, setUsuario } from "../auth.js";

// Modal "Minha conta": edita nome/e-mail e troca senha. onClose() fecha.
export function MinhaConta({ onClose }) {
  const u = getUser() || {};
  const [nome, setNome] = useState(u.nome || "");
  const [email, setEmail] = useState(u.email || "");
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [nova2, setNova2] = useState("");
  const [msg, setMsg] = useState("");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function salvar(e) {
    e.preventDefault();
    setErro(""); setMsg("");
    const body = {};
    if (nome.trim() && nome !== u.nome) body.nome = nome.trim();
    if (email.trim() && email !== u.email) body.email = email.trim();
    if (nova) {
      if (nova.length < 6) { setErro("A nova senha precisa de ao menos 6 caracteres."); return; }
      if (nova !== nova2) { setErro("A confirmação da nova senha não coincide."); return; }
      if (!atual) { setErro("Informe a senha atual para trocar a senha."); return; }
      body.senha_atual = atual; body.senha_nova = nova;
    }
    if (Object.keys(body).length === 0) { setMsg("Nada para salvar."); return; }
    setLoading(true);
    try {
      const novoUser = await api.updateMe(body);
      setUsuario(novoUser); // atualiza header/estado mantendo o token
      setMsg("Salvo ✓"); setAtual(""); setNova(""); setNova2("");
    } catch (err) {
      setErro(err.message || "falhou");
    } finally { setLoading(false); }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-slate-800">Minha conta</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>

        <form onSubmit={salvar} className="space-y-3">
          <label className="block text-sm">
            <span className="text-slate-500">Nome</span>
            <input className="input w-full mt-1" value={nome} onChange={(e) => setNome(e.target.value)} />
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">E-mail</span>
            <input className="input w-full mt-1" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>

          <div className="border-t border-slate-100 pt-3">
            <div className="text-xs text-slate-400 mb-2">Trocar senha (opcional)</div>
            <input className="input w-full mb-2" type="password" placeholder="Senha atual" value={atual}
              onChange={(e) => setAtual(e.target.value)} />
            <input className="input w-full mb-2" type="password" placeholder="Nova senha (mín. 6)" value={nova}
              onChange={(e) => setNova(e.target.value)} />
            <input className={`input w-full ${nova2 && nova !== nova2 ? "border-rose-400" : ""}`}
              type="password" placeholder="Confirmar nova senha" value={nova2}
              onChange={(e) => setNova2(e.target.value)} />
          </div>

          {erro && <p className="text-sm text-rose-600">{erro}</p>}
          {msg && <p className="text-sm text-emerald-600">{msg}</p>}

          <button disabled={loading}
            className="w-full bg-slate-900 hover:bg-slate-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
            {loading ? "Salvando…" : "Salvar alterações"}
          </button>
        </form>

        <button onClick={() => { sair(); onClose?.(); }}
          className="mt-3 text-xs text-rose-500 hover:text-rose-600 w-full text-center">
          Sair da conta
        </button>
      </div>
    </div>
  );
}
