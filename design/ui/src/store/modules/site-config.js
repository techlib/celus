import axios from 'axios'
import Vue from 'vue'

export default {

  state: {
    siteName: 'Celus',
    siteDomain: '',
    siteLogo: null,
    footerImages: [],
  },

  actions: {
    async loadSiteConfig ({commit}) {
      try {
        let response = await axios.get('/api/deployment/overview/', {privileged: true})
        commit('setSiteName', {siteName: response.data.site_name})
        commit('setSiteDomain', {siteDomain: response.data.site_domain})
        commit('setSiteLogo', {siteLogo: response.data.site_logo})
        commit('setFooterImages', {images: response.data.footer_images})
      } catch (error) {
        throw error
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
