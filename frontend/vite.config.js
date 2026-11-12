import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5468,
    proxy: {
      "/api": "http://127.0.0.1:5467",
      "/static": "http://127.0.0.1:5467",
    },
  },
  build: {
    outDir: "dist",
  },
});
