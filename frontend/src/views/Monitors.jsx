import { useEffect, useState } from "react";
import { api } from "../api";

const EMPTY = {
  nome: "", marca: "", marcaCodigo: "", modelo: "", versao: "",
  uf: "SP", cidade: "sao-paulo", preco_max: "", km_max: "", ano_min: "", threshold: 8,
};

export function Monitors() {
  const [monitors, setMonitors] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  // dados dos filtros em cascata (FIPE)
  const [marcas, setMarcas] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [versoes, setVersoes] = useState([]);
  const [loading, setLoading] = useState({ marcas: false, modelos: false, versoes: false });

  async function load() { setMonitors(await api.listMonitors()); }

  useEffect(() => {
    load();
    setLoading((l) => ({ ...l, marcas: true }));
    api.fipeMarcas().then(setMarcas).catch(() => setMarcas([]))
      .finally(() => setLoading((l) => ({ ...l, marcas: false })));
  }, []);

  // marca selecionada → carrega modelos
  async function onMarca(codigo) {
    const m = marcas.find((x) => x.codigo === codigo);
    setForm({ ...form, marcaCodigo: codigo, marca: m?.nome || "", modelo: "", versao: "" });
    setModelos([]); setVersoes([]);
    if (!codigo) return;
    setLoading((l) => ({ ...l, modelos: true }));
    try { setModelos(await api.fipeModelos(codigo)); }
    finally { setLoading((l) => ({ ...l, modelos: false })); }
  }

  // modelo selecionado → carrega versões
  async function onModelo(modelo) {
    setForm({ ...form, modelo, versao: "" });
    setVersoes([]);
    if (!modelo || !form.marcaCodigo) return;
    setLoading((l) => ({ ...l, versoes: true }));
    try { setVersoes(await api.fipeVersoes(form.marcaCodigo, modelo)); }
    finally { setLoading((l) => ({ ...l, versoes: false })); }
  }

  async function create(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const criterios = {
        marca: form.marca || undefined,
        modelo: form.modelo || undefined,
        versao: form.versao || undefined,
        uf: form.uf || undefined,
        cidade: form.cidade || undefined,
        preco_max: form.preco_max ? Number(form.preco_max) : undefined,
        km_max: form.km_max ? Number(form.km_max) : undefined,
        ano_min: form.ano_min ? Number(form.ano_min) : undefined,
      };
      await api.createMonitor({
        nome: form.nome || `${form.marca} ${form.modelo}`.trim() || "Novo monitor",
        criterios_json: criterios,
        threshold_desconto: Number(form.threshold) / 100,
        canais_notif: ["email"], status: "ativo",
      });
      setForm(EMPTY); setModelos([]); setVersoes([]);
      load();
    } finally { setSaving(false); }
  }

  async function toggle(m) {
    await api.updateMonitor(m.id, { status: m.status === "ativo" ? "pausado" : "ativo" });
    load();
  }
  async function remove(id) { await api.deleteMonitor(id); load(); }

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <form onSubmit={create} className="md:col-span-1 bg-white rounded-xl shadow-sm p-4 space-y-3 h-fit">
        <h2 className="font-semibold">Novo monitor</h2>
        <Input label="Nome" value={form.nome} onChange={(v) => setForm({ ...form, nome: v })} placeholder="opcional" />

        {/* Filtros em cascata FIPE */}
        <Select label={loading.marcas ? "Marca (carregando…)" : "Marca"} value={form.marcaCodigo}
          onChange={onMarca} disabled={loading.marcas}
          options={marcas.map((m) => ({ value: m.codigo, label: m.nome }))}
          placeholder="Selecione a marca" />

        <Select label={loading.modelos ? "Modelo (carregando…)" : "Modelo"} value={form.modelo}
          onChange={onModelo} disabled={!form.marcaCodigo || loading.modelos}
          options={modelos.map((m) => ({ value: m, label: m }))}
          placeholder={form.marcaCodigo ? "Selecione o modelo" : "escolha a marca primeiro"} />

        <Select label={loading.versoes ? "Versão (carregando…)" : "Versão"} value={form.versao}
          onChange={(v) => setForm({ ...form, versao: v })}
          disabled={!form.modelo || loading.versoes}
          options={versoes.map((v) => ({ value: v.nome, label: v.nome }))}
          placeholder={form.modelo ? "Todas as versões" : "escolha o modelo primeiro"} />

        <div className="grid grid-cols-2 gap-2">
          <Input label="UF" value={form.uf} onChange={(v) => setForm({ ...form, uf: v })} />
          <Input label="Cidade" value={form.cidade} onChange={(v) => setForm({ ...form, cidade: v })} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Input label="Preço máx." type="number" value={form.preco_max} onChange={(v) => setForm({ ...form, preco_max: v })} />
          <Input label="Km máx." type="number" value={form.km_max} onChange={(v) => setForm({ ...form, km_max: v })} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Input label="Ano mín." type="number" value={form.ano_min} onChange={(v) => setForm({ ...form, ano_min: v })} />
          <Input label="Notificar se ≥ (%)" type="number" value={form.threshold} onChange={(v) => setForm({ ...form, threshold: v })} />
        </div>
        <button disabled={saving} className="w-full bg-slate-900 hover:bg-slate-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {saving ? "Salvando…" : "Criar monitor"}
        </button>
      </form>

      <div className="md:col-span-2 space-y-3">
        {monitors.length === 0 && <p className="text-slate-400 text-sm">Nenhum monitor cadastrado.</p>}
        {monitors.map((m) => (
          <div key={m.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
            <div>
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
            <div className="flex gap-2">
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

function Input({ label, value, onChange, type = "text", placeholder }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <input type={type} value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)} className="input" />
    </label>
  );
}

function Select({ label, value, onChange, options, placeholder, disabled }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <select value={value} disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="input disabled:bg-slate-100 disabled:text-slate-400">
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
