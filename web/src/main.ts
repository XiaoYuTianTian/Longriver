import { createApp } from 'vue'
import App from './App.vue'
import { refreshBookmarks } from './lib/bookmarks'
import { ensureKnowledge } from './lib/knowledge'
import { router } from './router'
import './styles.css'
import 'maplibre-gl/dist/maplibre-gl.css'

refreshBookmarks()
ensureKnowledge().catch(() => undefined)

createApp(App).use(router).mount('#app')
