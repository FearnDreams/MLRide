import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    strictPort: true,
    hmr: {
      clientPort: 5175,
      overlay: false,
    },
    middlewareMode: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: false,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('代理错误:', err);
          });
          
          proxy.on('proxyReq', (proxyReq, req) => {
            console.log('发送请求到:', req.url);
            
            const headersToRemove = [
              'sec-ch-ua', 
              'sec-ch-ua-mobile', 
              'sec-ch-ua-platform',
              'upgrade-insecure-requests',
              'sec-fetch-site',
              'sec-fetch-mode',
              'sec-fetch-user',
              'sec-fetch-dest',
              'accept-encoding',
              'accept-language'
            ];
            
            headersToRemove.forEach(header => {
              proxyReq.removeHeader(header);
            });
          });
          
          proxy.on('proxyRes', (proxyRes, req, res) => {
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
            
            console.log(`响应状态: ${proxyRes.statusCode} ${req.url}`);
          });
        }
      },
    },
  },
  css: {
    postcss: './postcss.config.js',
  },
})
