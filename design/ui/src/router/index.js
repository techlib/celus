import Vue from 'vue'
import Router from 'vue-router'
import NotFoundPage from '../pages/NotFoundPage'
import ChartTestPage from '../pages/ChartTestPage'
import PlatformListPage from '../pages/PlatformListPage'
import PlatformDetailPage from '../pages/PlatformDetailPage'
import TitleDetailPage from '../pages/TitleDetailPage'
import AllTitlesListPage from '../pages/AllTitlesListPage'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'home',
      component: ChartTestPage
    },
    {
      path: '/platforms/',
      name: 'platform-list',
      component: PlatformListPage
    },
    {
      path: '/titles/',
      name: 'title-list',
      component: AllTitlesListPage
    },
    {
      path: '/platforms/:platformId',
      name: 'platform-detail',
      component: PlatformDetailPage,
      props: route => ({platformId: Number.parseInt(route.params.platformId, 10)})
    },
    {
      path: '/platforms/:platformId/title/:titleId',
      name: 'title-detail',
      component: TitleDetailPage,
      props: route => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        titleId: Number.parseInt(route.params.titleId, 10),
      })
    },
    {
      path: '*',
      component: NotFoundPage,
    }
  ],
  mode: 'history',
  linkActiveClass: 'is-active'
})
