import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({ plugins: [react(), tailwindcss()], server: { host: '127.0.0.1', proxy: {
 '/api': 'http://127.0.0.1:5000',
 '/policy-editor': 'http://127.0.0.1:5000',
 '/static': 'http://127.0.0.1:5000',
} } });
