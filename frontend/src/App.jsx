import { useEffect, useState } from "react";
import { api } from "./api";
import { getUser, isLogged, sair, revalidar } from "./auth.js";
import { carregarSalvos } from "./userdata.js";
import { Busca } from "./views/Busca.jsx";
import { Monitors } from "./views/Monitors.jsx";
import { Settings } from "./views/Settings.jsx";
import { Historico } from "./views/Historico.jsx";
import { Versoes } from "./views/Versoes.jsx";
import { Login } from "./views/Login.jsx";

const TABS = [
  { id: "busca", label: "Busca" },
  { id: "monitors", label: "Monitores" },
  { id: "historico", label: "Histórico" },
  { id: "settings", label: "Configurações" },
  { id: "versoes", label: "Versões" },
];

export default function App() {
  const [tab, setTab] = useState("busca");
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");
  const [abrir, setAbrir] = useState(null); // {criterios, filtro, nonce} → reabrir busca
  const [user, setUserState] = useState(getUser());
  const [showLogin, setShowLogin] = useState(false);

  // reage a login/logout em qualquer parte do app
  useEffect(() => {
    const onAuth = () => { setUserState(getUser()); carregarSalvos(); };
    window.addEventListener("auth-mudou", onAuth);
    revalidar();            // valida token salvo no boot
    if (isLogged()) carregarSalvos();
    return () => window.removeEventListener("auth-mudou", onAuth);
  }, []);

  function abrirBusca(entry) {
    setAbrir({ criterios: entry.criterios, filtro: entry.filtro, nonce: Date.now() });
    setTab("busca");
  }

  // Varredura com PROGRESSO REAL: dispara e faz polling do status até concluir.
  async function runNow() {
    setRunning(true);
    setMsg("Iniciando varredura…");
    try {
      const r = await api.runScrape();
      if (r.status === "ja_rodando") setMsg("Uma varredura já está em andamento…");
      for (let i = 0; i < 240; i++) {
        await new Promise((res) => setTimeout(res, 2500));
        const s = await api.scrapeStatus().catch(() => null);
        if (!s) continue;
        if (s.estado === "rodando") {
          if (!s.monitores_total) setMsg("Preparando varredura…");
          else setMsg(`⏳ Varrendo monitor ${Math.min((s.monitores_feitos || 0) + 1, s.monitores_total)}/${s.monitores_total}` +
            (s.monitor_atual ? ` (${s.monitor_atual})` : "") + " — entrando nos portais, ~30-60s por monitor…");
          continue;
        }
        if (s.erro) setMsg("Erro na varredura: " + s.erro);
        else if (s.resumo && s.resumo.monitores === 0)
          setMsg("Nenhum monitor cadastrado — a varredura roda os MONITORES. Crie um na aba Monitores (ou use a Busca direto).");
        else if (s.resumo)
          setMsg(`✓ Varredura concluída: ${s.resumo.monitores} monitor(es), ${s.resumo.resultados} resultados, ${s.resumo.notificados} alerta(s).`);
        else setMsg("✓ Varredura concluída.");
        window.dispatchEvent(new Event("varredura-concluida"));
        break;
      }
    } catch (e) {
      setMsg("Erro: " + e.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg sm:text-xl font-bold">🚗 CarPrice</h1>
            <p className="text-slate-400 text-xs sm:text-sm">Monitor de oportunidades em carros usados</p>
          </div>
          <div className="flex items-center gap-2">
            {user ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-slate-300 hidden sm:inline" title={user.email}>👤 {user.nome || user.email}</span>
                <button onClick={() => sair()} className="text-slate-400 hover:text-white text-xs px-2 py-1">Sair</button>
              </div>
            ) : (
              <button onClick={() => setShowLogin(true)}
                className="text-slate-200 hover:text-white text-sm border border-slate-600 rounded-lg px-3 py-2">
                Entrar
              </button>
            )}
            <button
              onClick={runNow}
              disabled={running}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 px-4 py-2 rounded-lg font-medium text-sm"
            >
              {running ? "⏳ Varrendo…" : "Varrer agora"}
            </button>
          </div>
        </div>
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap ${
                tab === t.id ? "border-emerald-400 text-white" : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {msg && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4">
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded-lg px-4 py-2">
            {msg}
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {tab === "busca" && <Busca abrir={abrir} />}
        {tab === "monitors" && <Monitors onPedirLogin={() => setShowLogin(true)} />}
        {tab === "historico" && <Historico onAbrirBusca={abrirBusca} onPedirLogin={() => setShowLogin(true)} />}
        {tab === "settings" && <Settings />}
        {tab === "versoes" && <Versoes />}
      </main>

      {showLogin && <Login onClose={() => setShowLogin(false)} onOk={() => setShowLogin(false)} />}
    </div>
  );
}
