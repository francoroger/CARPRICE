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

  async function runNow() {
    setRunning(true);
    setMsg("");
    try {
      await api.runScrape();
      setMsg("Varredura iniciada — os resultados aparecem em instantes.");
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
            {running ? "Rodando…" : "Varrer agora"}
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
