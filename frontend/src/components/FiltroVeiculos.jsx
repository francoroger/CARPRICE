import { useEffect, useState } from "react";
import { api } from "../api";

const CAMBIOS = ["Automático", "Automático CVT", "Manual"];
const COMBUSTIVEIS = ["Flex", "Gasolina", "Diesel", "Híbrido", "Elétrico"];

export const EMPTY_FILTRO = {
  marca: "", marcaCodigo: "", modelo: "", versao: "", uf: "SP", cidade: "", raio_km: "",
  ano_min: "", ano_max: "", preco_min: "", preco_max: "", km_min: "", km_max: "",
  cambio: "", combustivel: "", cor: "", condicao: "",
};

const NUMS = ["ano_min", "ano_max", "preco_min", "preco_max", "km_min", "km_max", "raio_km"];

// Monta o objeto de critérios da API a partir do estado do filtro.
export function criteriosFromFiltro(f) {
  const crit = {};
  for (const [k, v] of Object.entries(f)) {
    if (k === "marcaCodigo" || v === "" || v == null) continue;
    crit[k] = NUMS.includes(k) ? Number(v) : v;
  }
  return crit;
}

// Filtro de veículos compartilhado (Busca e Monitor). Controlado por value/onChange.
export function FiltroVeiculos({ value: f, onChange: setF }) {
  const [marcas, setMarcas] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [versoes, setVersoes] = useState([]);
  const [estados, setEstados] = useState([]);
  const [municipios, setMunicipios] = useState([]);

  useEffect(() => {
    api.fipeMarcas().then(setMarcas).catch(() => setMarcas([]));
    api.estados().then(setEstados).catch(() => setEstados([]));
    if (f.uf) api.municipios(f.uf).then(setMunicipios).catch(() => setMunicipios([]));
    // carrega modelos/versões se já vier preenchido (edição de monitor)
    if (f.marcaCodigo) api.fipeModelos(f.marcaCodigo).then(setModelos).catch(() => {});
    if (f.marcaCodigo && f.modelo) api.fipeVersoes(f.marcaCodigo, f.modelo).then(setVersoes).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onEstado(uf) {
    setF({ ...f, uf, cidade: "", raio_km: "" });
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
    setF({ ...f, modelo, versao: "" });
    setVersoes([]);
    if (modelo && f.marcaCodigo) setVersoes(await api.fipeVersoes(f.marcaCodigo, modelo).catch(() => []));
  }

  return (
    <div className="space-y-3">
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
        options={CAMBIOS.map((c) => ({ value: c, label: c }))} placeholder="Todos" />
      <Select label="Combustível" value={f.combustivel} onChange={(v) => setF({ ...f, combustivel: v })}
        options={COMBUSTIVEIS.map((c) => ({ value: c, label: c }))} placeholder="Todos" />

      <div className="text-sm">
        <span className="text-slate-500">Condição</span>
        <div className="flex gap-3 mt-1">
          {[["", "Todos"], ["0km", "0 km"], ["usado", "Usado"]].map(([v, lab]) => (
            <label key={v} className="flex items-center gap-1">
              <input type="radio" checked={f.condicao === v} onChange={() => setF({ ...f, condicao: v })} /> {lab}
            </label>
          ))}
        </div>
      </div>

      <Select label="Estado" value={f.uf} onChange={onEstado}
        options={estados.map((e) => ({ value: e.sigla, label: `${e.sigla} — ${e.nome}` }))}
        placeholder="Selecione o estado" />
      <Select label="Cidade" value={f.cidade} onChange={(v) => setF({ ...f, cidade: v, raio_km: v ? f.raio_km : "" })}
        disabled={!f.uf || municipios.length === 0}
        options={municipios.map((m) => ({ value: m, label: m }))}
        placeholder={f.uf ? "Todas as cidades" : "escolha o estado"} />

      {/* Raio de distância a partir da cidade */}
      <div className="text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Raio de distância</span>
          <span className="font-medium">{f.raio_km ? `${f.raio_km} km` : "padrão"}</span>
        </div>
        <input type="range" min="0" max="500" step="10" value={f.raio_km || 0}
          disabled={!f.cidade}
          onChange={(e) => setF({ ...f, raio_km: e.target.value === "0" ? "" : e.target.value })}
          className="w-full accent-red-600 disabled:opacity-40" />
        {!f.cidade && <span className="text-xs text-slate-400">selecione a cidade para usar o raio</span>}
      </div>
    </div>
  );
}

export function Select({ label, value, onChange, options, placeholder, disabled }) {
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
export function Inp({ ph, value, onChange }) {
  return <input type="number" placeholder={ph} value={value}
    onChange={(e) => onChange(e.target.value)} className="input w-full" />;
}
export function Group({ label, children }) {
  return (
    <div className="text-sm">
      <span className="text-slate-500">{label}</span>
      <div className="grid grid-cols-2 gap-2 mt-1">{children}</div>
    </div>
  );
}
