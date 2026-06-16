import { useState } from "react";
import { entrar, cadastrar } from "../auth.js";

// Modal de login/cadastro. onClose() fecha; onOk(user) após autenticar.
export function Login({ onClose, onOk }) {
  const [modo, setModo] = useState("login"); // "login" | "cadastro"
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senha2, setSenha2] = useState("");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErro("");
    if (modo === "cadastro") {
      if (senha.length < 6) { setErro("A senha precisa de ao menos 6 caracteres."); return; }
      if (senha !== senha2) { setErro("As senhas não coincidem."); return; }
    }
    setLoading(true);
    try {
      const u = modo === "login"
        ? await entrar(email, senha)
        : await cadastrar(nome, email, senha);
      onOk?.(u);
    } catch (err) {
      setErro(err.message || "falhou");
    } finally { setLoading(false); }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-slate-800">
            {modo === "login" ? "Entrar" : "Criar conta"}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          {modo === "cadastro" && (
            <input className="input w-full" placeholder="Nome" value={nome}
              onChange={(e) => setNome(e.target.value)} required />
          )}
          <input className="input w-full" type="email" placeholder="E-mail" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
          <input className="input w-full" type="password" placeholder="Senha (mín. 6)" value={senha}
            onChange={(e) => setSenha(e.target.value)} required minLength={6} />
          {modo === "cadastro" && (
            <input className={`input w-full ${senha2 && senha !== senha2 ? "border-rose-400" : ""}`}
              type="password" placeholder="Confirmar senha" value={senha2}
              onChange={(e) => setSenha2(e.target.value)} required />
          )}

          {erro && <p className="text-sm text-rose-600">{erro}</p>}

          <button disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
            {loading ? "…" : modo === "login" ? "Entrar" : "Criar conta"}
          </button>
        </form>

        <button onClick={() => { setErro(""); setSenha2(""); setModo(modo === "login" ? "cadastro" : "login"); }}
          className="mt-3 text-xs text-slate-500 hover:text-slate-700 w-full text-center">
          {modo === "login" ? "Não tem conta? Criar agora" : "Já tem conta? Entrar"}
        </button>

        <p className="mt-3 text-[11px] text-slate-400 text-center">
          Com conta, seus monitores, carros salvos e histórico ficam guardados e sincronizam entre dispositivos.
        </p>
      </div>
    </div>
  );
}
