import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const brl = (v) => (v == null ? "—" : "R$ " + v.toLocaleString("pt-BR"));
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");

export function Ranking() {
  const [items, setItems] = useState([]);
  const [origem, setOrigem] = useState("");
  const [descMin, setDescMin] = useState("");
  const [loading, setLoading] = useState(true);
  const [portalSel, setPortalSel] = useState("");

  const porPortal = useMemo(() => {
    const c = {};
    for (const l of items) c[l.portal_slug] = (c[l.portal_slug] || 0) + 1;
    return c;
  }, [items]);
  const filtered = useMemo(
    () => (portalSel ? items.filter((l) => l.portal_slug === portalSel) : items),
    [items, portalSel]
  );

  async function load() {
    setLoading(true);
    const p = new URLSearchParams();
    if (origem) p.set("origem", origem);
    if (descMin) p.set("desconto_min", String(Number(descMin) / 100));
    try {
      setItems(await api.listings("?" + p.toString()));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, [origem, descMin]);

  return (
    <div>
      <div className="flex flex-wrap gap-3 items-end mb-4">
        <Field label="Origem do score">
          <select value={origem} onChange={(e) => setOrigem(e.target.value)} className="input">
            <option value="">Todas</option>
            <option value="MERCADO">Mercado (idênticos)</option>
            <option value="FIPE">FIPE (fallback)</option>
          </select>
        </Field>
        <Field label="Desconto mínimo (%)">
          <input type="number" value={descMin} onChange={(e) => setDescMin(e.target.value)}
            placeholder="ex: 8" className="input w-28" />
        </Field>
        <span className="text-sm text-slate-500">{filtered.length} anúncios</span>
      </div>

      {/* FILTRO DE PORTAL */}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          <Chip ativo={portalSel === ""} onClick={() => setPortalSel("")} label={`Todos (${items.length})`} />
          {Object.entries(porPortal).sort((a, b) => b[1] - a[1]).map(([p, n]) => (
            <Chip key={p} ativo={portalSel === p} onClick={() => setPortalSel(p)} label={`${p} (${n})`} />
          ))}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead className="bg-slate-100 text-slate-600 text-left">
            <tr>
              <th className="px-3 py-2">Veículo</th>
              <th className="px-3 py-2">Ano</th>
              <th className="px-3 py-2">Km</th>
              <th className="px-3 py-2">Preço</th>
              <th className="px-3 py-2">Ref.</th>
              <th className="px-3 py-2">Desconto</th>
              <th className="px-3 py-2">Origem</th>
              <th className="px-3 py-2">Portal</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-400">Carregando…</td></tr>}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-400">
                Nenhum anúncio ainda. Clique em “Varrer agora”.
              </td></tr>
            )}
            {filtered.map((l) => (
              <tr key={l.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 max-w-xs">
                  <a href={l.url} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">
                    {l.versao || l.titulo || "—"}
                  </a>
                  {l.cidade && <span className="text-slate-400"> · {l.cidade}/{l.uf}</span>}
                </td>
                <td className="px-3 py-2">{l.ano_modelo || "—"}</td>
                <td className="px-3 py-2">{l.km ? l.km.toLocaleString("pt-BR") : "—"}</td>
                <td className="px-3 py-2 font-medium">{brl(l.preco)}</td>
                <td className="px-3 py-2 text-slate-500">{brl(l.preco_ref)}</td>
                <td className={`px-3 py-2 font-semibold ${(l.desconto ?? 0) > 0 ? "text-emerald-600" : "text-rose-500"}`}>
                  {pct(l.desconto)}
                </td>
                <td className="px-3 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${l.origem_score === "MERCADO" ? "bg-emerald-100 text-emerald-700" : l.origem_score === "FIPE" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                    {l.origem_score || "—"}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-500">{l.portal_slug}</td>
              </tr>
            ))}
          </tbody>
        </table>
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

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      {children}
    </label>
  );
}
