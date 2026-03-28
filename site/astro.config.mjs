import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://trialfinder.co',
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    sitemap({
      serialize(item) {
        item.lastmod = new Date().toISOString();
        if (item.url === 'https://trialfinder.co/') item.priority = 1.0;
        else if (item.url.includes('/condition/')) item.priority = 0.9;
        else if (item.url.includes('/trial/')) item.priority = 0.8;
        else if (item.url.includes('/guides/')) item.priority = 0.7;
        else if (item.url.includes('/state/')) item.priority = 0.6;
        else item.priority = 0.5;
        return item;
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
    build: {
      chunkSizeWarningLimit: 2000,
    },
  },
});
