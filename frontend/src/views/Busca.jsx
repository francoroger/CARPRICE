import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const brl = (v) => (v == null ? "—" : "R$ " + v.toLocaleString("pt-BR"));
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");

const CAMBIOS = ["", "Automático", "Automático CVT", "Manual"];
const COMBUSTIVEIS = ["", "Flex", "Gasolina", "Diesel", "Híbrido", "Elétrico"];
const EMPTY = {
  marca: "", marcaCodigo: "", modelo: "", versao: "", uf: "SP", cidade: "",
  ano_min: "", ano_max: "", preco_min: "", preco_max: "", km_min: "", km_max: "",
  cambio: "", combustivel: "", cor: "", condicao: "",
};

export function Busca() {
  const [f, setF] = useState(EMPTY);
  const [marcas, setMarcas] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [versoes, setVersoes] = useState([]);
  const [estados, setEstados] = useState([]);
  const [municipios, setMunicipios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);
  const [ordem, setOrdem] = useState("preco_asc");

  // re-ordena no cliente (instantâneo, sem re-buscar)
  const ordenados = useMemo(() => {
    if (!res?.resultados) return [];
    const r = [...res.resultados];
    if (ordem === "preco_desc") r.sort((a, b) => (b.preco || 0) - (a.preco || 0));
    else if (ordem === "desconto") r.sort((a, b) => (b.desconto ?? -9) - (a.desconto ?? -9));
    else r.sort((a, b) => (a.preco || 1e12) - (b.preco || 1e12));
    return r;
  }, [res, ordem]);

  useEffect(() => {
    api.fipeMarcas().then(setMarcas).catch(() => setMarcas([]));
    api.estados().then(setEstados).catch(() => setEstados([]));
    api.municipios("SP").then(setMunicipios).catch(() => setMunicipios([]));
  }, []);

  async function onEstado(uf) {
    setF({ ...f, uf, cidade: "" });
    setMunicipios([]);
    if (uf) setMunicipios(await api.municipios(uf).catch(() => []));
  }

  async function onMarca(codigo) {
    const m = marcas.find((x) => x.codigo === codigo);
    setF({ ...f, marcaCodigo: codigo, marca: m?.nome || "", modelo: "", versao: "" });
    setModelos([]); setVersoes([]);
    if (codigo) setModelos(await api.fipeModelos(codigo).catch(() => []));
  }
  async function onModelo(modelo) {
    setF({ ...f, modelo, versao: "" }); setVersoes([]);
    if (modelo && f.marcaCodigo) setVersoes(await api.fipeVersoes(f.marcaCodigo, modelo).catch(() => []));
  }

  async function buscar(e) {
    e.preventDefault();
    setLoading(true); setRes(null);
    try {
      const crit = {};
      for (const [k, v] of Object.entries(f)) {
        if (k === "marcaCodigo" || v === "" || v == null) continue;
        crit[k] = ["ano_min", "ano_max", "preco_min", "preco_max", "km_min", "km_max"].includes(k)
          ? Number(v) : v;
      }
      setRes(await api.search(crit));
    } catch (err) {
      setRes({ erro: String(err), resultados: [], portais: [] });
    } finally { setLoading(false); }
  }

  return (
    <div className="grid lg:grid-cols-4 gap-6">
      {/* FILTROS (estilo CarroSP) */}
      <form onSubmit={buscar} className="lg:col-span-1 bg-white rounded-xl shadow-sm p-4 space-y-3 h-fit">
        <h2 className="font-semibold text-red-600">Filtro de Veículos</h2>

        <Select label="Marca" value={f.marcaCodigo} onChange={onMarca}
          options={marcas.map((m) => ({ value: m.codigo, label: m.nome }))} placeholder="Todas as marcas" />
        <Select label="Modelo" value={f.modelo} onChange={onModelo} disabled={!f.marcaCodigo}
          options={modelos.map((m) => ({ value: m, label: m }))} placeholder="Todos os modelos" />
        <Select label="Versão" value={f.versao} onChange={(v) => setF({ ...f, versao: v })} disabled={!f.modelo}
          options={versoes.map((v) => ({ value: v.nome, label: v.nome }))} placeholder="Todas as versões" />

        <Group label="Ano">
          <Inp ph="De" value={f.ano_min} onChange={(v) => setF({ ...f, ano_min: v })} />
          <Inp ph="Até" value={f.ano_max} onChange={(v) => setF({ ...f, ano_max: v })} />
        </Group>
        <Group label="Preço (R$)">
          <Inp ph="De" value={f.preco_min} onChange={(v) => setF({ ...f, preco_min: v })} />
          <Inp ph="Até" value={f.preco_max} onChange={(v) => setF({ ...f, preco_max: v })} />
        </Group>
        <Group label="Quilometragem">
          <Inp ph="De" value={f.km_min} onChange={(v) => setF({ ...f, km_min: v })} />
          <Inp ph="Até" value={f.km_max} onChange={(v) => setF({ ...f, km_max: v })} />
        </Group>

        <Select label="Câmbio" value={f.cambio} onChange={(v) => setF({ ...f, cambio: v })}
          options={CAMBIOS.slice(1).map((c) => ({ value: c, label: c }))} placeholder="Todos" />
        <Select label="Combustível" value={f.combustivel} onChange={(v) => setF({ ...f, combustivel: v })}
          options={COMBUSTIVEIS.slice(1).map((c) => ({ value: c, label: c }))} placeholder="Todos" />

        <div className="text-sm">
          <span className="text-slate-500">Condição</span>
          <div className="flex gap-3 mt-1">
            {[["", "Todos"], ["0km", "0 km"], ["usado", "Usado"]].map(([v, lab]) => (
              <label key={v} className="flex items-center gap-1">
                <input type="radio" name="cond" checked={f.condicao === v}
                  onChange={() => setF({ ...f, condicao: v })} /> {lab}
              </label>
            ))}
          </div>
        </div>

        <Select label="Estado" value={f.uf} onChange={onEstado}
          options={estados.map((e) => ({ value: e.sigla, label: `${e.sigla} — ${e.nome}` }))}
          placeholder="Selecione o estado" />
        <Select label="Cidade" value={f.cidade} onChange={(v) => setF({ ...f, cidade: v })}
          disabled={!f.uf || municipios.length === 0}
          options={municipios.map((m) => ({ value: m, label: m }))}
          placeholder={f.uf ? "Todas as cidades" : "escolha o estado"} />

        <button disabled={loading} className="w-full bg-red-600 hover:bg-red-500 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {loading ? "Buscando em todos os portais…" : "🔎 Buscar agora"}
        </button>
      </form>

      {/* RESULTADOS */}
      <div className="lg:col-span-3">
        {loading && <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
          Entrando em todos os portais ao vivo… (alguns segundos)
        </div>}

        {res && !loading && (
          <>
            <div className="flex flex-wrap gap-2 mb-3 items-center">
              <span className="font-semibold">{res.total} veículos encontrados</span>
              <select value={ordem} onChange={(e) => setOrdem(e.target.value)}
                className="input ml-auto text-sm py-1">
                <option value="preco_asc">Preço: menor → maior</option>
                <option value="preco_desc">Preço: maior → menor</option>
                <option value="desconto">Melhor desconto</option>
              </select>
            </div>
            <div className="flex flex-wrap gap-1 mb-3">
              {(res.portais || []).map((p) => (
                <span key={p.portal} className={`text-xs px-2 py-0.5 rounded ${p.status === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-500"}`}>
                  {p.portal}: {p.qtd}
                </span>
              ))}
            </div>
            {res.erro && <p className="text-rose-600 text-sm">{res.erro}</p>}

            {res.resultados.length === 0 && (
              <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
                Nenhum veículo com esses filtros.
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {ordenados.map((l) => <CarCard key={l.id} l={l} />)}
            </div>
          </>
        )}

        {!res && !loading && (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
            Escolha os filtros e clique em <b>Buscar agora</b> — entro em todos os portais na hora.
          </div>
        )}
      </div>
    </div>
  );
}

function CarCard({ l }) {
  const desc = l.desconto;
  const bom = (desc ?? 0) > 0;
  return (
    <a href={l.url} target="_blank" rel="noreferrer"
      className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow flex flex-col">
      <div className="relative aspect-[4/3] bg-slate-100">
        {l.foto_url ? (
          <img src={l.foto_url} alt={l.versao || ""} loading="lazy"
            className="w-full h-full object-cover"
            onError={(e) => { e.currentTarget.style.display = "none"; }} />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-300 text-4xl">🚗</div>
        )}
        {desc != null && (
          <span className={`absolute top-2 left-2 text-xs font-bold px-2 py-1 rounded ${bom ? "bg-emerald-500 text-white" : "bg-slate-700/80 text-white"}`}>
            {bom ? "▼ " : ""}{pct(desc)}
          </span>
        )}
        <span className="absolute top-2 right-2 text-[10px] uppercase tracking-wide bg-black/55 text-white px-2 py-0.5 rounded">
          {l.portal_slug}
        </span>
      </div>
      <div className="p-3 flex flex-col gap-1 flex-1">
        <div className="text-sm font-semibold text-slate-800 leading-tight line-clamp-2 min-h-[2.4em]">
          {l.versao || l.titulo || "Veículo"}
        </div>
        <div className="text-lg font-bold text-red-600">{brl(l.preco)}</div>
        <div className="text-xs text-slate-500 flex flex-wrap gap-x-2">
          <span>{l.ano_modelo || "—"}</span>
          <span>·</span>
          <span>{l.km != null ? l.km.toLocaleString("pt-BR") + " km" : "km n/d"}</span>
          {l.cidade && <><span>·</span><span>{l.cidade}/{l.uf}</span></>}
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs">
          {l.preco_ref ? (
            <span className="text-slate-400">ref {brl(l.preco_ref)}</span>
          ) : <span className="text-slate-300">sem referência</span>}
          {l.origem_score && (
            <span className={`px-1.5 py-0.5 rounded ${l.origem_score === "MERCADO" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
              {l.origem_score}
            </span>
          )}
        </div>
      </div>
    </a>
  );
}

function Inp({ ph, value, onChange }) {
  return <input type="number" placeholder={ph} value={value}
    onChange={(e) => onChange(e.target.value)} className="input w-full" />;
}
function Group({ label, children }) {
  return (
    <div className="text-sm">
      <span className="text-slate-500">{label}</span>
      <div className="grid grid-cols-2 gap-2 mt-1">{children}</div>
    </div>
  );
}
function Select({ label, value, onChange, options, placeholder, disabled }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <select value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}
        className="input disabled:bg-slate-100 disabled:text-slate-400">
        <option value="">{placeholder}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
