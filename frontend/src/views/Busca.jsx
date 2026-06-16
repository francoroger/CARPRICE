import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { EMPTY_FILTRO, FiltroVeiculos, criteriosFromFiltro } from "../components/FiltroVeiculos.jsx";
import { classifica, origemLabel, pctScore } from "../score.js";
import { salvarBusca, lerBusca, registrarBusca, estaSalvo, alternarSalvo } from "../storage.js";

const brl = (v) => (v == null ? "—" : "R$ " + v.toLocaleString("pt-BR"));

// critérios (da API) → filtro (do formulário). marcaCodigo não vem nos critérios,
// então o cascata não recarrega os dropdowns, mas a BUSCA usa os campos corretos.
function filtroDeCriterios(c = {}) {
  return { ...EMPTY_FILTRO, ...c, ano_min: c.ano_min ?? "", ano_max: c.ano_max ?? "" };
}

export function Busca({ abrir }) {
  // restaura o estado da última busca (sobrevive ao refresh)
  const inicial = lerBusca() || {};
  const [f, setF] = useState(inicial.f || EMPTY_FILTRO);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(inicial.res || null);
  const [ordem, setOrdem] = useState(inicial.ordem || "preco_asc");
  const [portalSel, setPortalSel] = useState(inicial.portalSel || "");

  // persiste o estado a cada mudança
  useEffect(() => { salvarBusca({ f, res, ordem, portalSel }); }, [f, res, ordem, portalSel]);

  // "Refazer" do Histórico → restaura o filtro e busca (abrir.nonce muda a cada clique)
  useEffect(() => {
    if (!abrir?.criterios) return;
    setF(abrir.filtro || filtroDeCriterios(abrir.criterios));
    executar(abrir.criterios, false, abrir.filtro);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abrir?.nonce]);

  const porPortal = useMemo(() => {
    const c = {};
    for (const l of res?.resultados || []) c[l.portal_slug] = (c[l.portal_slug] || 0) + 1;
    return c;
  }, [res]);

  const lista = useMemo(() => {
    let r = [...(res?.resultados || [])];
    if (portalSel) r = r.filter((l) => l.portal_slug === portalSel);
    if (ordem === "preco_desc") r.sort((a, b) => (b.preco || 0) - (a.preco || 0));
    else if (ordem === "desconto") r.sort((a, b) => (b.desconto ?? -9) - (a.desconto ?? -9));
    else r.sort((a, b) => (a.preco || 1e12) - (b.preco || 1e12));
    return r;
  }, [res, ordem, portalSel]);

  async function executar(criterios, forcar = false, filtro = null) {
    setLoading(true); setRes(null); setPortalSel("");
    try {
      const r = await api.search({ ...criterios, forcar });
      setRes(r);
      registrarBusca(criterios, r.total ?? r.resultados?.length ?? 0, filtro);
    } catch (err) {
      setRes({ erro: String(err), resultados: [], portais: [] });
    } finally { setLoading(false); }
  }
  function buscar(e, forcar = false) {
    if (e && e.preventDefault) e.preventDefault();
    executar(criteriosFromFiltro(f), forcar, f);
  }

  return (
    <div className="grid lg:grid-cols-4 gap-6">
      <form onSubmit={buscar} className="lg:col-span-1 bg-white rounded-xl shadow-sm p-4 space-y-3 h-fit">
        <h2 className="font-semibold text-red-600">Filtro de Veículos</h2>
        <FiltroVeiculos value={f} onChange={setF} />
        <button disabled={loading}
          className="w-full bg-red-600 hover:bg-red-500 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {loading ? "Buscando em todos os portais…" : "🔎 Buscar agora"}
        </button>
      </form>

      <div className="lg:col-span-3">
        {loading && <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
          Entrando em todos os portais ao vivo… (alguns segundos)
        </div>}

        {res && !loading && (
          <>
            <div className="flex flex-wrap gap-2 mb-3 items-center">
              <span className="font-semibold">{lista.length} veículos</span>
              {(res.portais || []).some((p) => p.portal === "cache") && (
                <span className="text-xs text-slate-400">(cache)</span>
              )}
              <button onClick={() => buscar(null, true)}
                className="ml-auto text-sm px-3 py-1 rounded border border-slate-200 hover:bg-slate-50">
                ↻ Atualizar
              </button>
              <select value={ordem} onChange={(e) => setOrdem(e.target.value)} className="input text-sm py-1">
                <option value="preco_asc">Preço: menor → maior</option>
                <option value="preco_desc">Preço: maior → menor</option>
                <option value="desconto">Melhor negócio</option>
              </select>
            </div>

            {res.resultados?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-4">
                <Chip ativo={portalSel === ""} onClick={() => setPortalSel("")}
                  label={`Todos (${res.resultados.length})`} />
                {Object.entries(porPortal).sort((a, b) => b[1] - a[1]).map(([p, n]) => (
                  <Chip key={p} ativo={portalSel === p} onClick={() => setPortalSel(p)} label={`${p} (${n})`} />
                ))}
              </div>
            )}

            {res.erro && <p className="text-rose-600 text-sm">{res.erro}</p>}
            {lista.length === 0 && !res.erro && (
              <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
                Nenhum veículo com esses filtros.
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {lista.map((l) => <CarCard key={l.id || l.url} l={l} />)}
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

function Chip({ ativo, onClick, label }) {
  return (
    <button onClick={onClick}
      className={`text-xs px-2.5 py-1 rounded-full border ${ativo
        ? "bg-slate-900 text-white border-slate-900"
        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"}`}>
      {label}
    </button>
  );
}

// onSalvarMudou: callback opcional (ex.: na página Histórico, p/ remover ao clicar)
export function CarCard({ l, onSalvarMudou }) {
  const cls = classifica(l.desconto);
  const [salvo, setSalvo] = useState(() => estaSalvo(l.url));
  function toggleSalvar(e) {
    e.preventDefault(); e.stopPropagation();
    const agora = alternarSalvo(l);
    setSalvo(agora);
    window.dispatchEvent(new Event("salvos-mudou"));
    onSalvarMudou?.(agora);
  }
  return (
    <a href={l.url} target="_blank" rel="noreferrer"
      className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow flex flex-col">
      <div className="relative aspect-[4/3] bg-slate-100">
        {l.foto_url ? (
          <img src={l.foto_url} alt={l.versao || ""} loading="lazy" className="w-full h-full object-cover"
            onError={(e) => { e.currentTarget.style.display = "none"; }} />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-300 text-4xl">🚗</div>
        )}
        {cls && (
          <span className={`absolute top-2 left-2 text-xs font-bold px-2 py-1 rounded ${cls.cor}`}>
            {cls.icone} {cls.rotulo}
          </span>
        )}
        <button onClick={toggleSalvar} title={salvo ? "Remover dos salvos" : "Salvar carro"}
          className={`absolute top-2 right-2 text-base leading-none rounded-full w-7 h-7 flex items-center justify-center ${salvo ? "bg-amber-400 text-white" : "bg-black/55 text-white hover:bg-black/75"}`}>
          {salvo ? "★" : "☆"}
        </button>
        <span className="absolute bottom-2 right-2 text-[10px] uppercase tracking-wide bg-black/55 text-white px-2 py-0.5 rounded">
          {l.portal_slug}
        </span>
      </div>
      <div className="p-3 flex flex-col gap-1 flex-1">
        <div className="text-sm font-semibold text-slate-800 leading-tight line-clamp-2 min-h-[2.4em]">
          {l.versao || l.titulo || "Veículo"}
        </div>
        <div className="text-lg font-bold text-red-600">{brl(l.preco)}</div>
        <div className="text-xs text-slate-500 flex flex-wrap gap-x-2">
          <span>{l.ano_modelo || "—"}</span><span>·</span>
          <span>{l.km != null ? l.km.toLocaleString("pt-BR") + " km" : "km n/d"}</span>
          {l.cidade && <><span>·</span><span>{l.cidade}/{l.uf}</span></>}
        </div>
        <div className="mt-1 text-xs text-slate-500">
          {l.desconto != null && l.preco_ref ? (
            <>
              <span className={l.desconto >= 0.05 ? "text-emerald-600 font-semibold" : l.desconto <= -0.05 ? "text-rose-500 font-semibold" : ""}>
                {pctScore(l.desconto)} do mercado
              </span>
              <span className="text-slate-400"> · justo {brl(l.preco_ref)}</span>
              {origemLabel(l.origem_score) && (
                <div className="text-slate-400">comparado com {origemLabel(l.origem_score)}</div>
              )}
            </>
          ) : (
            <span className="text-slate-300">sem comparáveis suficientes</span>
          )}
        </div>
      </div>
    </a>
  );
}
