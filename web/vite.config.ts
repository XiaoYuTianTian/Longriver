import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { detailArtPlugin } from './detailArtPlugin'

const root = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.resolve(root, '../content/dist')

export default defineConfig({
  plugins: [vue(), detailArtPlugin(distDir)],
  publicDir: distDir,
  server: {
    fs: {
      allow: [path.resolve(root, '..')],
    },
  },
})
