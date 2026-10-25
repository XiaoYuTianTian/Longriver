import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const root = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [vue()],
  publicDir: path.resolve(root, '../content/dist'),
  server: {
    fs: {
      allow: [path.resolve(root, '..')],
    },
  },
})
