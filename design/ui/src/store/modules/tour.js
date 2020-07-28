import axios from 'axios'

export default {

  state: {
    tours: [
      {
        name: 'basic',
        title: 'basic_tour_title',
      },
    ]
  },

  getters: {
    tourFinished (state, getters, rootState) {
      return name => rootState.user && rootState.user.extra_data && rootState.user.extra_data[getters.tourBackendAttrName(name)]
    },
    tourNeverSeen (state, getters, rootState) {
      return name => !(rootState.user && rootState.user.extra_data && rootState.user.extra_data.hasOwnProperty(getters.tourBackendAttrName(name)))
    },
    tourByName (state) {
      return (name) => {
        let matching = state.tours.filter(item => item.name === name)
        if (matching.length) {
          return matching[0]
        }
        return null
      }
    },
    tourBackendAttrName () {
      return name => `${name}_tour_finished`
    }
  },

  actions: {
    async backstageChangeTourStatus ({commit, getters}, {tourName, status}) {
      try {
        let key = getters.tourBackendAttrName(tourName)
        let data = {}
        data[key] = status
        let response = await axios.post(
          '/api/user/extra-data',
          data
          )
        commit('storeUserExtraData', {extraData: response.data})
      } catch (error) {
        console.warn('Could not save tour status')
        throw error
      }
    },
    activateTour ({commit, getters}, {name}) {
      commit('modifyUserExtraData', {key: getters.tourBackendAttrName(name), value: false})
    }
  },
}
