import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

const localhostApiUrlPattern = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i;
const httpApiUrlPattern = /^https?:\/\//i;

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrl = env.VITE_API_URL?.trim();

  if (command === "build" && mode === "production") {
    if (!apiUrl) {
      throw new Error(
        "VITE_API_URL deve apontar para a API publica no build de producao.",
      );
    }

    if (!httpApiUrlPattern.test(apiUrl)) {
      throw new Error(
        "VITE_API_URL deve ser uma URL absoluta iniciando com http:// ou https://.",
      );
    }

    if (localhostApiUrlPattern.test(apiUrl)) {
      throw new Error(
        "VITE_API_URL nao pode apontar para localhost no build de producao.",
      );
    }
  }

  return {
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
    },
    plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
