import { useEffect, useState } from "react";
import { api } from "../api";
import { isLogged } from "../auth.js";
import { EMPTY_FILTRO, FiltroVeiculos, Inp, criteriosFromFiltro } from "../components/FiltroVeiculos.jsx";
import { CarCard } from "./Busca.jsx";

const FREQUENCIAS = [[30, "30 minutos"], [60, "1 hora"], [180, "3 horas"],
  [360, "6 horas"], [720, "12 horas"], [1440, "1 dia"]];
const rotuloFreq = (min) => {
  const f = FREQUENCIAS.find(([v]) => v === min);
  return f ? `a cada ${f[1]}` : `a cada ${min} min`;
};
const quando = (iso) => {
  const d = (Date.now() - Date.parse(iso)) / 1000;
  if (d < 3600) return `há ${Math.max(1, Math.floor(d / 60))} min`;
  if (d < 86400) return `há ${Math.floor(d / 3600)} h`;
  return new Date(iso).toLocaleDateString("pt-BR");
};

export function Monitors({ onPedirLogin }) {
  const [monitors, setMonitors] = useState([]);
  const [filtro, setFiltro] = useState(EMPTY_FILTRO);
  const [nome, setNome] = useState("");
  const [threshold, setThreshold] = useState(8);
  const [frequencia, setFrequencia] = useState(60);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  // resultados do monitor aberto: { id, nome, lista, loading }
  const [res, setRes] = useState(null);

  const logado = isLogged();
  async function load() { setMonitors(await api.listMonitors()); }
  useEffect(() => {
    load();
    const recar = () => load();  // recarrega ao logar/deslogar (escopo muda)
    const recarrega = () => setRes((r) => { if (r) verResultados({ id: r.id, nome: r.nome, criterios_json: r.criterios }); return r; });
    window.addEventListener("auth-mudou", recar);
    window.addEventListener("varredura-concluida", recarrega);
    return () => {
      window.removeEventListener("auth-mudou", recar);
      window.removeEventListener("varredura-concluida", recarrega);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function create(e) {
    e.preventDefault();
    if (!logado) { onPedirLogin?.(); return; }
    setSaving(true); setErro("");
    try {
      const criterios = criteriosFromFiltro(filtro);
      delete criterios.marcaCodigo;
      await api.createMonitor({
        nome: nome || `${filtro.marca} ${filtro.modelo}`.trim() || "Novo monitor",
        criterios_json: criterios,
        threshold_desconto: Number(threshold) / 100,
        frequencia_min: Number(frequencia),
        canais_notif: ["email"], status: "ativo",
      });
      setFiltro(EMPTY_FILTRO); setNome(""); setThreshold(8); setFrequencia(60);
      load();
    } catch (err) {
      setErro(err.message || "não foi possível criar o monitor");
    } finally { setSaving(false); }
  }

  async function toggle(m) {
    setErro("");
    try { await api.updateMonitor(m.id, { status: m.status === "ativo" ? "pausado" : "ativo" }); load(); }
    catch (err) { setErro(err.message); }
  }
  async function remove(id) {
    if (!confirm("Excluir este monitor?")) return;
    setErro("");
    try {
      await api.deleteMonitor(id);
      setRes((r) => (r && r.id === id ? null : r));
      load();
    } catch (err) { setErro(err.message); }
  }

  // Mostra OS CARROS que o monitor encontra: mesma busca dos critérios dele.
  // Vem do cache da última varredura/busca (<30min) → instantâneo.
  async function verResultados(m) {
    setRes({ id: m.id, nome: m.nome, criterios: m.criterios_json, lista: [], loading: true });
    try {
      const r = await api.search({ ...(m.criterios_json || {}) });
      setRes({ id: m.id, nome: m.nome, criterios: m.criterios_json, lista: r.resultados, loading: false });
    } catch {
      setRes({ id: m.id, nome: m.nome, criterios: m.criterios_json, lista: [], loading: false, erro: true });
    }
  }

  return (
    <div className="space-y-4">
      {!logado && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-2 flex items-center justify-between gap-3">
          <span>Entre numa conta para que seus monitores fiquem salvos e rodem a varredura automática.</span>
          <button onClick={onPedirLogin} className="text-xs font-medium bg-amber-500 text-white rounded px-3 py-1 hover:bg-amber-400 shrink-0">
            Entrar / criar conta
          </button>
        </div>
      )}
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

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">Verificar a cada</span>
          <select value={frequencia} onChange={(e) => setFrequencia(e.target.value)} className="input">
            {FREQUENCIAS.map(([v, lab]) => <option key={v} value={v}>{lab}</option>)}
          </select>
        </label>

        {erro && <p className="text-sm text-rose-600">{erro}</p>}

        <button disabled={saving}
          className="w-full bg-slate-900 hover:bg-slate-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {saving ? "Salvando…" : logado ? "Criar monitor" : "Entrar para criar monitor"}
        </button>
      </form>

      <div className="lg:col-span-2 space-y-3">
        {monitors.length === 0 && <p className="text-slate-400 text-sm">Nenhum monitor cadastrado.</p>}
        {monitors.map((m) => (
          <div key={m.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between gap-3 flex-wrap">
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
                notificar ≥ {(m.threshold_desconto * 100).toFixed(0)}% · {rotuloFreq(m.frequencia_min)}
                {" · "}{m.ultima_exec_em ? `última verificação ${quando(m.ultima_exec_em)}` : "ainda não verificado"}
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => verResultados(m)}
                className="text-sm px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-500 font-medium">
                Ver resultados
              </button>
              <button onClick={() => toggle(m)} className="text-sm px-3 py-1 rounded border border-slate-200 hover:bg-slate-50">
                {m.status === "ativo" ? "Pausar" : "Ativar"}
              </button>
              <button onClick={() => remove(m.id)} className="text-sm px-3 py-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50">
                Excluir
              </button>
            </div>
          </div>
        ))}

        {/* RESULTADOS DO MONITOR — os carros que ele encontra agora */}
        {res && (
          <div className="pt-2">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">
                Resultados de “{res.nome}”
                {!res.loading && <span className="text-slate-400 font-normal"> — {res.lista.length} carros (mais barato primeiro)</span>}
              </h3>
              <button onClick={() => setRes(null)} className="text-sm text-slate-400 hover:text-slate-600">✕ fechar</button>
            </div>
            {res.loading && <p className="text-sm text-slate-400">⏳ Buscando os carros do monitor…</p>}
            {res.erro && <p className="text-sm text-rose-500">Erro ao buscar — tente de novo.</p>}
            {!res.loading && !res.erro && res.lista.length === 0 && (
              <p className="text-sm text-slate-400">Nenhum carro encontrado com esses critérios agora.</p>
            )}
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {res.lista.map((l) => <CarCard key={l.id} l={l} />)}
            </div>
          </div>
        )}
      </div>
    </div>
    </div>
  );
}
