// Tradução do score (Preço de Mercado) em rótulos intuitivos.
// desconto: fração acima(-)/abaixo(+) do preço justo. Limiares calibrados na
// análise de mercado (dispersão típica ±11,5% dentro de modelo+ano).

export function classifica(desconto) {
  if (desconto == null) return null;
  if (desconto >= 0.10) return { rotulo: "Excelente negócio", cor: "bg-emerald-600 text-white", icone: "🔥" };
  if (desconto >= 0.05) return { rotulo: "Bom preço", cor: "bg-emerald-100 text-emerald-700", icone: "▼" };
  if (desconto > -0.05) return { rotulo: "Preço justo", cor: "bg-slate-100 text-slate-600", icone: "" };
  if (desconto > -0.12) return { rotulo: "Acima do mercado", cor: "bg-amber-100 text-amber-700", icone: "▲" };
  return { rotulo: "Caro", cor: "bg-rose-100 text-rose-700", icone: "▲" };
}

// "VERSAO:8" → "8 anúncios da mesma versão" | "MODELO:23" → "23 do mesmo modelo"
export function origemLabel(origem) {
  if (!origem) return null;
  const [tipo, n] = origem.split(":");
  if (tipo === "VERSAO") return `${n} da mesma versão`;
  if (tipo === "MODELO") return `${n} do mesmo modelo`;
  if (tipo === "FIPE") return "tabela FIPE";
  return origem; // compat com dados antigos (MERCADO/FIPE)
}

export const pctScore = (v) =>
  v == null ? "—" : `${v > 0 ? "" : ""}${Math.abs(v * 100).toFixed(0)}% ${v >= 0 ? "abaixo" : "acima"}`;
