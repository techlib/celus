import axios from 'axios'
import Vue from 'vue'
import sleep from '@/libs/sleep'

export default {

  state: {
    siteName: 'Celus',
    siteDomain: '',
    siteLogo: null,
    footerImages: [],
  },

  actions: {
    async loadSiteConfig ({commit}) {
      while (true) {
        try {
          let response = await axios.get('/api/deployment/overview/', {privileged: true})
          commit('setSiteName', {siteName: response.data.site_name})
          commit('setSiteDomain', {siteDomain: response.data.site_domain})
          commit('setSiteLogo', {siteLogo: response.data.site_logo})
          commit('setFooterImages', {images: response.data.footer_images})
          break
        } catch (error) {
          // wait 2 s and retry
          commit('setBackendReady', false)
          await sleep(2000)
        }
      }
    }
  },

  mutations: {
    setSiteName (state, {siteName}) {
      state.siteName = siteName
    },
    setSiteDomain (state, {siteDomain}) {
      state.siteDomain = siteDomain
    },
    setSiteLogo (state, {siteLogo}) {
      state.siteLogo = siteLogo
    },
    setFooterImages (state, {images}) {
      Vue.set(state, 'footerImages', images)
    },
  }
}
