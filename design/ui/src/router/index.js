import Vue from 'vue'
import Router from 'vue-router'
import NotFoundPage from '../pages/NotFoundPage'
import ChartTestPage from '../pages/ChartTestPage'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'home',
      component: ChartTestPage
    },
     {
      path: '*',
      component: NotFoundPage,
    }
  ],
  mode: 'history',
  linkActiveClass: 'is-active'
})
