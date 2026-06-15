import { useEffect, useMemo, useState } from "react";

const TIPO_COR = {
  Added: "bg-emerald-100 text-emerald-700",
  Changed: "bg-sky-100 text-sky-700",
  Fixed: "bg-amber-100 text-amber-700",
  Removed: "bg-rose-100 text-rose-700",
  Known: "bg-slate-100 text-slate-600",
};
const TIPO_PT = { Added: "Novo", Changed: "Mudou", Fixed: "Corrigido", Removed: "Removido", Known: "Limitação" };

// markdown mínimo inline: **negrito** e `código`
function md(texto) {
  const partes = [];
  const re = /\*\*(.+?)\*\*|`(.+?)`/g;
  let i = 0, m;
  while ((m = re.exec(texto))) {
    if (m.index > i) partes.push(texto.slice(i, m.index));
    if (m[1] != null) partes.push(<strong key={m.index}>{m[1]}</strong>);
    else partes.push(<code key={m.index} className="bg-slate-100 text-slate-700 rounded px-1 text-[0.85em]">{m[2]}</code>);
    i = re.lastIndex;
  }
  if (i < texto.length) partes.push(texto.slice(i));
  return partes;
}

// Parse do CHANGELOG (Keep a Changelog) em [{versao, data, secoes:[{tipo, itens:[...]}]}]
function parseChangelog(texto) {
  const blocos = texto.split(/\n## \[/).slice(1); // 1º pedaço é o cabeçalho
  return blocos
    .map((b) => {
      const fimCab = b.indexOf("\n");
      const cab = b.slice(0, fimCab);
      const mm = cab.match(/^([^\]]+)\]\s*(?:-\s*(.+))?$/);
      const versao = mm ? mm[1].trim() : cab.trim();
      const data = mm && mm[2] ? mm[2].trim() : "";
      const corpo = b.slice(fimCab + 1);
      const secoes = [];
      // prefixa \n p/ o split pegar TAMBÉM a 1ª seção (que começa em "### ")
      const partes = ("\n" + corpo).split(/\n### /);
      for (const sec of partes) {
        const lin = sec.split("\n");
        const tipo = lin[0].trim();
        if (!["Added", "Changed", "Fixed", "Removed", "Known"].includes(tipo)) continue;
        const itens = [];
        let atual = "";
        for (const l of lin.slice(1)) {
          if (l.startsWith("- ")) { if (atual) itens.push(atual); atual = l.slice(2).trim(); }
          else if (l.trim() && atual) atual += " " + l.trim(); // continuação de linha
        }
        if (atual) itens.push(atual);
        if (itens.length) secoes.push({ tipo, itens });
      }
      return { versao, data, secoes };
    })
    .filter((v) => !/não lançado/i.test(v.versao));
}

export function Historico() {
  const [changelog, setChangelog] = useState(null);
  const [version, setVersion] = useState("");
  const [erro, setErro] = useState(false);

  useEffect(() => {
    fetch("/CHANGELOG.md").then((r) => r.ok ? r.text() : Promise.reject()).then(setChangelog).catch(() => setErro(true));
    fetch("/VERSION").then((r) => r.ok ? r.text() : "").then((t) => setVersion(t.trim())).catch(() => {});
  }, []);

  const versoes = useMemo(() => (changelog ? parseChangelog(changelog) : []), [changelog]);
  const totalAlteracoes = useMemo(
    () => versoes.reduce((n, v) => n + v.secoes.reduce((s, sec) => s + sec.itens.length, 0), 0),
    [versoes]
  );

  if (erro) return <p className="text-slate-400 text-sm">Não foi possível carregar o histórico.</p>;
  if (!changelog) return <p className="text-slate-400 text-sm">Carregando histórico…</p>;

  const atual = versoes[0];
  return (
    <div className="max-w-3xl">
      {/* topo: versão atual + última alteração em destaque */}
      <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 className="text-xl font-bold text-red-600">CarPrice v{version || (atual && atual.versao)}</h2>
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">versão atual</span>
          <span className="text-sm text-slate-400">{versoes.length} versões · {totalAlteracoes} alterações</span>
        </div>
        {atual && (
          <div className="mt-3">
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">Última edição implementada</div>
            <ul className="space-y-1">
              {atual.secoes.flatMap((sec) =>
                sec.itens.map((it, j) => (
                  <li key={sec.tipo + j} className="text-sm text-slate-700 flex gap-2">
                    <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded h-fit ${TIPO_COR[sec.tipo]}`}>{TIPO_PT[sec.tipo]}</span>
                    <span>{md(it)}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>

      {/* linha do tempo de todas as versões */}
      <div className="space-y-4">
        {versoes.map((v, idx) => (
          <div key={v.versao} className="bg-white rounded-xl shadow-sm p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={`font-bold ${idx === 0 ? "text-red-600" : "text-slate-700"}`}>v{v.versao}</span>
              {v.data && <span className="text-xs text-slate-400">{v.data}</span>}
            </div>
            {v.secoes.map((sec) => (
              <div key={sec.tipo} className="mb-2 last:mb-0">
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${TIPO_COR[sec.tipo]}`}>{TIPO_PT[sec.tipo]}</span>
                <ul className="mt-1 ml-1 space-y-1">
                  {sec.itens.map((it, j) => (
                    <li key={j} className="text-sm text-slate-600 flex gap-2">
                      <span className="text-slate-300">•</span><span>{md(it)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
