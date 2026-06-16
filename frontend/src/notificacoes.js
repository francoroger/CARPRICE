// Notificações do navegador + controle de "alertas já vistos".
const SEEN_KEY = "carprice.alertas.seen";

export const getSeen = () => Number(localStorage.getItem(SEEN_KEY) || 0);
export const setSeen = (id) => localStorage.setItem(SEEN_KEY, String(id || 0));

export const suportaNotif = () => typeof window !== "undefined" && "Notification" in window;
export const permissaoNotif = () => (suportaNotif() ? Notification.permission : "unsupported");

export async function pedirPermissaoNotif() {
  if (!suportaNotif()) return "unsupported";
  if (Notification.permission === "default") return Notification.requestPermission();
  return Notification.permission;
}

export function notificar(titulo, corpo) {
  if (suportaNotif() && Notification.permission === "granted") {
    try { new Notification(titulo, { body: corpo, icon: "/vite.svg" }); } catch { /* alguns browsers bloqueiam */ }
  }
}
