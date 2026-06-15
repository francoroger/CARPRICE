import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const CAMBIOS = ["Automático", "Automático CVT", "Manual"];
const COMBUSTIVEIS = ["Flex", "Gasolina", "Diesel", "Híbrido", "Elétrico"];

export const EMPTY_FILTRO = {
  marca: "", marcaCodigo: "", modelo: "", versao: "",
  uf: "SP", cidade: "", raio_km: "",
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
  const [acordando, setAcordando] = useState(true); // backend free hiberna (~50s)

  useEffect(() => {
    let vivo = true;
    // RETRY com backoff: o Render free hiberna e a 1ª chamada falha/demora —
    // sem isso os dropdowns ficavam vazios até o usuário dar F5.
    (async () => {
      for (let i = 0; i < 36 && vivo; i++) {        // ~3 min de tentativas
        try {
          const ms = await api.fipeMarcas();
          if (!vivo) return;
          if (ms?.length) {
            setMarcas(ms);
            setAcordando(false);
            api.estados().then((e) => vivo && setEstados(e)).catch(() => {});
            if (f.uf) api.municipios(f.uf).then((m) => vivo && setMunicipios(m)).catch(() => {});
            if (f.marcaCodigo) api.fipeModelos(f.marcaCodigo).then((m) => vivo && setModelos(m)).catch(() => {});
            if (f.marcaCodigo && f.modelo)
              api.fipeVersoes(f.marcaCodigo, f.modelo).then((v) => vivo && setVersoes(v)).catch(() => {});
            return;
          }
        } catch { /* servidor ainda acordando */ }
        await new Promise((r) => setTimeout(r, 5000));
      }
      if (vivo) setAcordando(false);
    })();
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- vínculo ano <-> versão (dados de ano vêm em cada versão da FIPE) --- #
  const temAnos = useMemo(() => versoes.some((v) => (v.anos || []).length), [versoes]);
  // versão selecionada limita os anos; senão união de todas as versões.
  const anosDisponiveis = useMemo(() => {
    const vObj = versoes.find((v) => v.nome === f.versao);
    const base = vObj && (vObj.anos || []).length
      ? vObj.anos
      : [...new Set(versoes.flatMap((v) => v.anos || []))];
    return base.slice().sort((a, b) => b - a);
  }, [versoes, f.versao]);
  // faixa de ano selecionada limita as versões: mostra as que existem na faixa.
  const versoesFiltradas = useMemo(() => {
    if (!temAnos) return versoes; // sem dados de ano → não filtra (não esvazia)
    const de = Number(f.ano_min) || null;
    const ate = Number(f.ano_max) || null;
    if (!de && !ate) return versoes;
    return versoes.filter((v) =>
      (v.anos || []).some((a) => (!de || a >= de) && (!ate || a <= ate)));
  }, [versoes, temAnos, f.ano_min, f.ano_max]);

  async function onEstado(uf) {
    setF({ ...f, uf, cidade: "", raio_km: "" });
    setMunicipios([]);
    if (uf) setMunicipios(await api.municipios(uf).catch(() => []));
  }
  async function onMarca(codigo) {
    const m = marcas.find((x) => x.codigo === codigo);
    setF({ ...f, marcaCodigo: codigo, marca: m?.nome || "", modelo: "", versao: "",
           ano_min: "", ano_max: "" });
    setModelos([]); setVersoes([]);
    if (codigo) setModelos(await api.fipeModelos(codigo).catch(() => []));
  }
  async function onModelo(modelo) {
    setF({ ...f, modelo, versao: "", ano_min: "", ano_max: "" });
    setVersoes([]);
    if (modelo && f.marcaCodigo) setVersoes(await api.fipeVersoes(f.marcaCodigo, modelo).catch(() => []));
  }
  // escolher a faixa de ANO (De/Até): corrige faixa invertida e limpa a versão
  // se ela não existir mais dentro da faixa.
  function onAnoFaixa(campo, valor) {
    let de = campo === "ano_min" ? valor : f.ano_min;
    let ate = campo === "ano_max" ? valor : f.ano_max;
    if (de && ate && Number(de) > Number(ate)) {
      if (campo === "ano_min") ate = de;   // ajusta o outro lado
      else de = ate;
    }
    const vObj = versoes.find((v) => v.nome === f.versao);
    const nDe = Number(de) || null, nAte = Number(ate) || null;
    const versaoOk = !vObj || (vObj.anos || []).some(
      (a) => (!nDe || a >= nDe) && (!nAte || a <= nAte));
    setF({ ...f, ano_min: de, ano_max: ate, versao: versaoOk ? f.versao : "" });
  }
  // escolher a VERSÃO: se a faixa atual não cobre nenhum ano dela, ajusta a
  // faixa para o intervalo da versão.
  function onVersao(nome) {
    const vObj = versoes.find((v) => v.nome === nome);
    const anos = vObj ? vObj.anos || [] : [];
    const nDe = Number(f.ano_min) || null, nAte = Number(f.ano_max) || null;
    const faixaOk = !anos.length ||
      anos.some((a) => (!nDe || a >= nDe) && (!nAte || a <= nAte));
    if (faixaOk) setF({ ...f, versao: nome });
    else setF({ ...f, versao: nome,
                ano_min: String(Math.min(...anos)), ano_max: String(Math.max(...anos)) });
  }

  return (
    <div className="space-y-3">
      <Select label="Marca" value={f.marcaCodigo} onChange={onMarca}
        options={marcas.map((m) => ({ value: m.codigo, label: m.nome }))}
        placeholder={acordando ? "⏳ acordando o servidor… (até 1 min)" : "Todas as marcas"} />
      {acordando && (
        <p className="text-xs text-amber-600">
          O servidor gratuito hiberna quando fica parado — as marcas carregam sozinhas em instantes.
        </p>
      )}
      <Select label="Modelo" value={f.modelo} onChange={onModelo} disabled={!f.marcaCodigo}
        options={modelos.map((m) => ({ value: m, label: m }))} placeholder="Todos os modelos" />

      {/* Faixa de ANO (vínculo FIPE): De/Até com os anos reais do modelo */}
      {f.modelo && temAnos ? (
        <Group label="Ano">
          <select value={f.ano_min} onChange={(e) => onAnoFaixa("ano_min", e.target.value)}
            className="input">
            <option value="">De</option>
            {anosDisponiveis.map((a) => <option key={a} value={String(a)}>{a}</option>)}
          </select>
          <select value={f.ano_max} onChange={(e) => onAnoFaixa("ano_max", e.target.value)}
            className="input">
            <option value="">Até</option>
            {anosDisponiveis.map((a) => <option key={a} value={String(a)}>{a}</option>)}
          </select>
        </Group>
      ) : (
        <Group label="Ano">
          <Inp ph="De" value={f.ano_min} maxLen={4} onChange={(v) => setF({ ...f, ano_min: v })} />
          <Inp ph="Até" value={f.ano_max} maxLen={4} onChange={(v) => setF({ ...f, ano_max: v })} />
        </Group>
      )}

      <Select label="Versão" value={f.versao} onChange={onVersao} disabled={!f.modelo}
        options={versoesFiltradas.map((v) => ({ value: v.nome, label: v.nome }))}
        placeholder={f.modelo && temAnos && (f.ano_min || f.ano_max)
          ? `Versões de ${f.ano_min || "…"}–${f.ano_max || "…"}`
          : "Todas as versões"} />
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
// Entrada numérica robusta: só dígitos (bloqueia "-", "e", ".", colar lixo).
// `maxLen` limita o nº de dígitos (ex.: 4 p/ ano). Sem decimais/negativos.
export function Inp({ ph, value, onChange, maxLen }) {
  return (
    <input type="text" inputMode="numeric" placeholder={ph} value={value}
      onChange={(e) => {
        let v = e.target.value.replace(/\D/g, "");
        if (maxLen) v = v.slice(0, maxLen);
        onChange(v);
      }}
      className="input w-full" />
  );
}
export function Group({ label, children }) {
  return (
    <div className="text-sm">
      <span className="text-slate-500">{label}</span>
      <div className="grid grid-cols-2 gap-2 mt-1">{children}</div>
    </div>
  );
}
