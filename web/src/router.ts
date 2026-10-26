import { createRouter, createWebHistory } from 'vue-router'
import AtlasView from './views/AtlasView.vue'

function detailQuery(to: { params: Record<string, string | string[]> }, key: 'claim' | 'person' | 'place') {
  const id = to.params.id
  return { path: '/', query: { [key]: String(Array.isArray(id) ? id[0] : id) } }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'atlas', component: AtlasView },
    { path: '/browse', redirect: '/' },
    { path: '/mine', redirect: '/' },
    { path: '/claims/:id', redirect: (to) => detailQuery(to, 'claim') },
    { path: '/people/:id', redirect: (to) => detailQuery(to, 'person') },
    { path: '/places/:id', redirect: (to) => detailQuery(to, 'place') },
  ],
})
