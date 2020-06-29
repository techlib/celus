import axios from 'axios'

export default {

  state: {
    noInterestPlatformsCount: 0,
    noInterestPlatformsWithDataCount: 0,
    sushiCredentialsCount: 0,
  },

  getters: {
    getNotifications (state) {
      // returns an object mapping URL name to an object describing the notifications to show
      let ret = {}
      if (state.noInterestPlatformsWithDataCount > 0) {
        ret['maintenance'] = {
          tooltip: 'no_interest_platforms_with_data_present',
          level: 'warning',
        }
      } else if (state.noInterestPlatformsCount > 0) {
        ret['maintenance'] = {
          tooltip: 'no_interest_platforms_present',
          level: 'info',
        }
      }
      return ret
    }
  },

  actions: {
    async fetchNoInterestPlatforms ({commit, dispatch, rootState}) {
      const url = `/api/organization/-1/platform/no-interest-defined/`
      try {
        const response = await axios.get(url)
        commit('setNoInterestPlatformsCount', {count: response.data.length})
        commit('setNoInterestPlatformsWithDataCount', {count: response.data.filter(item => item.has_data).length})
        return response.data
      } catch (error) {
        dispatch('showSnackbar', {content: 'Error fetching data: ' + error, color: 'error'})
      }
      return []
    },
    async loadSushiCredentialsCount ({commit, dispatch}) {
      try {
        let response = await axios.get('/api/sushi-credentials/count/')
        commit('setSushiCredentialsCount', response.data)
      } catch(error) {
        dispatch('showSnackbar', {content: 'Error loading sushi credentials count: ' + error, color: 'error'})
      }
    },
  },

  mutations: {
    setNoInterestPlatformsCount (state, {count}) {
      state.noInterestPlatformsCount = count
    },
    setNoInterestPlatformsWithDataCount (state, {count}) {
      state.noInterestPlatformsWithDataCount = count
    },
    setSushiCredentialsCount (state, {count}) {
      state.sushiCredentialsCount = count
    }
  }
}
