import { useEffect, useState } from "react";
import { lerHistorico, limparHistorico, removerDoHistorico, lerSalvos, removerSalvo } from "../storage.js";
import { CarCard } from "./Busca.jsx";

const brl = (v) => (v == null ? "—" : "R$ " + v.toLocaleString("pt-BR"));
const quando = (ts) => {
  const d = (Date.now() - ts) / 1000;
  if (d < 60) return "agora";
  if (d < 3600) return `${Math.floor(d / 60)} min atrás`;
  if (d < 86400) return `${Math.floor(d / 3600)} h atrás`;
  return new Date(ts).toLocaleDateString("pt-BR");
};

// onAbrirBusca(criterios): pedido para a aba Busca reabrir esses critérios.
export function Historico({ onAbrirBusca }) {
  const [hist, setHist] = useState([]);
  const [salvos, setSalvos] = useState([]);

  function recarrega() { setHist(lerHistorico()); setSalvos(lerSalvos()); }
  useEffect(() => {
    recarrega();
    window.addEventListener("salvos-mudou", recarrega);
    return () => window.removeEventListener("salvos-mudou", recarrega);
  }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <p className="text-xs text-slate-400">
        Seu histórico e carros salvos ficam guardados neste navegador — não se perdem ao atualizar a página.
      </p>

      {/* CARROS SALVOS */}
      <section>
        <h2 className="font-semibold mb-3">Carros salvos <span className="text-slate-400 font-normal">({salvos.length})</span></h2>
        {salvos.length === 0 ? (
          <p className="text-sm text-slate-400">Nenhum carro salvo. Clique no ⭐ de um carro na Busca para salvá-lo aqui.</p>
        ) : (
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {salvos.map((c) => (
              <CarCard key={c.url} l={c} onSalvarMudou={() => { removerSalvo(c.url); recarrega(); }} />
            ))}
          </div>
        )}
      </section>

      {/* HISTÓRICO DE BUSCAS */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Buscas recentes <span className="text-slate-400 font-normal">({hist.length})</span></h2>
          {hist.length > 0 && (
            <button onClick={() => { limparHistorico(); recarrega(); }}
              className="text-xs text-slate-400 hover:text-rose-500">limpar tudo</button>
          )}
        </div>
        {hist.length === 0 ? (
          <p className="text-sm text-slate-400">Nenhuma busca ainda. Suas buscas aparecem aqui para refazer com um clique.</p>
        ) : (
          <div className="bg-white rounded-xl shadow-sm divide-y divide-slate-100">
            {hist.map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <button onClick={() => onAbrirBusca?.(h)} className="flex-1 text-left min-w-0">
                  <div className="font-medium text-slate-800 truncate">{h.label}</div>
                  <div className="text-xs text-slate-400">{quando(h.ts)} · {h.total ?? 0} resultados</div>
                </button>
                <button onClick={() => onAbrirBusca?.(h)}
                  className="text-xs px-3 py-1 rounded bg-slate-900 text-white hover:bg-slate-700 shrink-0">
                  Refazer
                </button>
                <button onClick={() => { removerDoHistorico(h.id); recarrega(); }}
                  className="text-slate-300 hover:text-rose-500 shrink-0" title="remover">✕</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
