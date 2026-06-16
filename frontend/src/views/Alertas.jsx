import { useEffect, useState } from "react";
import { api } from "../api";
import { isLogged } from "../auth.js";
import { CarCard } from "./Busca.jsx";

const quando = (iso) => {
  const ts = Date.parse(iso);
  const d = (Date.now() - ts) / 1000;
  if (d < 60) return "agora";
  if (d < 3600) return `${Math.floor(d / 60)} min atrás`;
  if (d < 86400) return `${Math.floor(d / 3600)} h atrás`;
  return new Date(ts).toLocaleDateString("pt-BR");
};

export function Alertas({ onPedirLogin }) {
  const [lista, setLista] = useState(null);
  const logado = isLogged();

  useEffect(() => {
    if (!logado) { setLista([]); return; }
    api.alerts().then(setLista).catch(() => setLista([]));
    const recar = () => api.alerts().then(setLista).catch(() => {});
    window.addEventListener("varredura-concluida", recar);
    return () => window.removeEventListener("varredura-concluida", recar);
  }, [logado]);

  if (!logado) {
    return (
      <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3 max-w-xl">
        Entre numa conta para receber alertas dos seus monitores aqui.
        <button onClick={onPedirLogin} className="ml-2 text-xs font-medium bg-amber-500 text-white rounded px-3 py-1 hover:bg-amber-400">
          Entrar
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <div className="bg-sky-50 border border-sky-200 text-sky-800 text-sm rounded-lg px-4 py-2 mb-4">
        💡 Aqui aparecem os carros que <b>seus monitores</b> encontraram abaixo do preço de mercado (acima do seu
        limite de desconto). A varredura roda sozinha de tempos em tempos. Você também recebe por e-mail quando
        o envio estiver ativado.
      </div>

      {lista === null && <p className="text-sm text-slate-400">Carregando alertas…</p>}
      {lista && lista.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-8 text-center text-slate-400">
          Nenhum alerta ainda. Crie um monitor na aba <b>Monitores</b> e, quando ele achar uma oportunidade,
          ela aparece aqui.
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {(lista || []).map((a) => (
          <div key={a.id}>
            <div className="text-xs text-slate-400 mb-1">🔔 {a.monitor} · {quando(a.quando)}</div>
            <CarCard l={a} />
          </div>
        ))}
      </div>
    </div>
  );
}
