// Copia CHANGELOG.md e VERSION (raiz do repo) para public/ — assim o front lê a
// MESMA fonte de verdade do versionamento, sem duplicar conteúdo no código.
// Roda no prebuild/predev (Netlify base=frontend → repo root é "..").
import { copyFileSync, mkdirSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");   // raiz do repositório
const pub = resolve(here, "..", "public");
mkdirSync(pub, { recursive: true });

for (const f of ["CHANGELOG.md", "VERSION"]) {
  try {
    copyFileSync(resolve(root, f), resolve(pub, f));
    console.log("copy-meta: copiado", f);
  } catch (e) {
    console.warn("copy-meta: pulou", f, "-", e.message);
  }
}
