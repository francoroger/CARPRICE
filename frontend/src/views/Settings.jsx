import { useEffect, useState } from "react";
import { api } from "../api";

export function Settings() {
  const [score, setScore] = useState(null);
  const [portals, setPortals] = useState([]);
  const [logs, setLogs] = useState([]);
  const [saved, setSaved] = useState(false);

  async function load() {
    setScore(await api.scoreParams());
    setPortals(await api.portals());
    setLogs(await api.scrapeLogs());
  }
  useEffect(() => { load(); }, []);

  async function saveScore() {
    await api.saveScore({
      faixas_km: String(score.faixas_km).split(",").map((s) => Number(s.trim())).filter(Boolean),
      min_grupo: Number(score.min_grupo),
      w_km: Number(score.w_km),
      threshold_desconto: Number(score.threshold_desconto),
      metrica_ref: score.metrica_ref,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function togglePortal(p) {
    await api.togglePortal(p.slug, !p.ativo);
    load();
  }

  if (!score) return <p className="text-slate-400">Carregando…</p>;

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <section className="bg-white rounded-xl shadow-sm p-4 space-y-3">
        <h2 className="font-semibold">Parâmetros do score</h2>
        <Row label="Faixas de km (vírgula)">
          <input className="input" value={score.faixas_km}
            onChange={(e) => setScore({ ...score, faixas_km: e.target.value })} />
        </Row>
        <Row label="Mín. anúncios p/ usar mercado">
          <input className="input" type="number" value={score.min_grupo}
            onChange={(e) => setScore({ ...score, min_grupo: e.target.value })} />
        </Row>
        <Row label="Peso do bônus de km (w_km)">
          <input className="input" type="number" step="0.01" value={score.w_km}
            onChange={(e) => setScore({ ...score, w_km: e.target.value })} />
        </Row>
        <Row label="Threshold de desconto (0–1)">
          <input className="input" type="number" step="0.01" value={score.threshold_desconto}
            onChange={(e) => setScore({ ...score, threshold_desconto: e.target.value })} />
        </Row>
        <Row label="Métrica de referência">
          <select className="input" value={score.metrica_ref}
            onChange={(e) => setScore({ ...score, metrica_ref: e.target.value })}>
            <option value="mediana">mediana</option>
            <option value="media">média</option>
          </select>
        </Row>
        <button onClick={saveScore} className="bg-slate-900 hover:bg-slate-700 text-white rounded-lg px-4 py-2 text-sm font-medium">
          {saved ? "Salvo ✓" : "Salvar parâmetros"}
        </button>
      </section>

      <section className="bg-white rounded-xl shadow-sm p-4">
        <h2 className="font-semibold mb-3">Portais</h2>
        <div className="space-y-2">
          {portals.map((p) => (
            <div key={p.slug} className="flex items-center justify-between text-sm">
              <span>
                {p.nome}
                {p.min_tier > 1 && <span className="ml-2 text-xs text-amber-600">nível {p.min_tier}</span>}
              </span>
              <button onClick={() => togglePortal(p)}
                className={`px-3 py-1 rounded text-xs font-medium ${p.ativo ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-500"}`}>
                {p.ativo ? "ativo" : "inativo"}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-xl shadow-sm p-4 md:col-span-2">
        <h2 className="font-semibold mb-3">Últimas varreduras</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-left">
            <tr><th className="py-1">Portal</th><th>Status</th><th>Resultados</th><th>Nível</th><th>Duração</th><th>Erro</th></tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t border-slate-100">
                <td className="py-1">{l.portal_id}</td>
                <td className={l.status === "ok" ? "text-emerald-600" : "text-rose-500"}>{l.status}</td>
                <td>{l.qtd_resultados}</td>
                <td>{l.tier_usado}</td>
                <td>{l.duracao_ms} ms</td>
                <td className="text-slate-400 max-w-xs truncate">{l.erro || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      {children}
    </label>
  );
}
