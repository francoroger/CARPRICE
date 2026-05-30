import { useEffect, useState } from "react";
import { api } from "../api";
import { EMPTY_FILTRO, FiltroVeiculos, Inp, criteriosFromFiltro } from "../components/FiltroVeiculos.jsx";

export function Monitors() {
  const [monitors, setMonitors] = useState([]);
  const [filtro, setFiltro] = useState(EMPTY_FILTRO);
  const [nome, setNome] = useState("");
  const [threshold, setThreshold] = useState(8);
  const [saving, setSaving] = useState(false);

  async function load() { setMonitors(await api.listMonitors()); }
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const criterios = criteriosFromFiltro(filtro);
      delete criterios.marcaCodigo;
      await api.createMonitor({
        nome: nome || `${filtro.marca} ${filtro.modelo}`.trim() || "Novo monitor",
        criterios_json: criterios,
        threshold_desconto: Number(threshold) / 100,
        canais_notif: ["email"], status: "ativo",
      });
      setFiltro(EMPTY_FILTRO); setNome(""); setThreshold(8);
      load();
    } finally { setSaving(false); }
  }

  async function toggle(m) {
    await api.updateMonitor(m.id, { status: m.status === "ativo" ? "pausado" : "ativo" });
    load();
  }
  async function remove(id) { await api.deleteMonitor(id); load(); }

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <form onSubmit={create} className="lg:col-span-1 bg-white rounded-xl shadow-sm p-4 space-y-3 h-fit">
        <h2 className="font-semibold text-red-600">Novo monitor</h2>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">Nome (opcional)</span>
          <input value={nome} onChange={(e) => setNome(e.target.value)} className="input" placeholder="ex.: Onix barato em SP" />
        </label>

        <FiltroVeiculos value={filtro} onChange={setFiltro} />

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">Notificar quando o desconto for ≥ (%)</span>
          <Inp ph="8" value={threshold} onChange={setThreshold} />
        </label>

        <button disabled={saving}
          className="w-full bg-slate-900 hover:bg-slate-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {saving ? "Salvando…" : "Criar monitor"}
        </button>
      </form>

      <div className="lg:col-span-2 space-y-3">
        {monitors.length === 0 && <p className="text-slate-400 text-sm">Nenhum monitor cadastrado.</p>}
        {monitors.map((m) => (
          <div key={m.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium flex items-center gap-2">
                {m.nome}
                <span className={`text-xs px-2 py-0.5 rounded ${m.status === "ativo" ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}>
                  {m.status}
                </span>
              </div>
              <div className="text-sm text-slate-500 mt-1">
                {Object.entries(m.criterios_json || {}).filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join("  ·  ") || "sem filtros"}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                notificar ≥ {(m.threshold_desconto * 100).toFixed(0)}% · a cada {m.frequencia_min} min
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => toggle(m)} className="text-sm px-3 py-1 rounded border border-slate-200 hover:bg-slate-50">
                {m.status === "ativo" ? "Pausar" : "Ativar"}
              </button>
              <button onClick={() => remove(m.id)} className="text-sm px-3 py-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50">
                Excluir
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
