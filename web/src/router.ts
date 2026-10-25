import { createRouter, createWebHistory } from 'vue-router'
import AtlasView from './views/AtlasView.vue'
import BrowseView from './views/BrowseView.vue'
import ClaimView from './views/ClaimView.vue'
import MineView from './views/MineView.vue'
import PersonView from './views/PersonView.vue'
import PlaceView from './views/PlaceView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'atlas', component: AtlasView },
    { path: '/browse', name: 'browse', component: BrowseView },
    { path: '/mine', name: 'mine', component: MineView },
    { path: '/claims/:id', name: 'claim', component: ClaimView, props: true },
    { path: '/people/:id', name: 'person', component: PersonView, props: true },
    { path: '/places/:id', name: 'place', component: PlaceView, props: true },
  ],
})
