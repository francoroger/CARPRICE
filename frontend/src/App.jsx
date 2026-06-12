import { useEffect, useState } from "react";
import { api } from "./api";
import { Busca } from "./views/Busca.jsx";
import { Monitors } from "./views/Monitors.jsx";
import { Ranking } from "./views/Ranking.jsx";
import { Settings } from "./views/Settings.jsx";

const TABS = [
  { id: "busca", label: "Busca" },
  { id: "ranking", label: "Ranking" },
  { id: "monitors", label: "Monitores" },
  { id: "settings", label: "Configurações" },
];

export default function App() {
  const [tab, setTab] = useState("busca");
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

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
          setMsg(`✓ Varredura concluída: ${s.resumo.monitores} monitor(es), ${s.resumo.resultados} resultados, ${s.resumo.notificados} alerta(s). Veja o Ranking.`);
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
          <button
            onClick={runNow}
            disabled={running}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 px-4 py-2 rounded-lg font-medium text-sm"
          >
            {running ? "⏳ Varrendo…" : "Varrer agora"}
          </button>
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
        {tab === "busca" && <Busca />}
        {tab === "ranking" && <Ranking />}
        {tab === "monitors" && <Monitors />}
        {tab === "settings" && <Settings />}
      </main>
    </div>
  );
}
