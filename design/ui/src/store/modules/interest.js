import axios from 'axios'

export default {

  state: {
    interestGroups: [],
    selectedGroups: [],
  },

  getters: {
    selectedGroupObjects: state => state.interestGroups.filter(item => state.selectedGroups.indexOf(item.short_name) > -1)
  },

  actions: {
    async fetchInterestGroups({commit, dispatch}) {
      try {
        let response = await axios.get('/api/interest-groups/')
        commit('setInterestGroups', {interestGroups: response.data})
        commit(
          'setSelectedGroups',
          {groups: response.data.filter(item => item.important).map(item => item.short_name)}
        )
      } catch (error) {
        dispatch(
          'showSnackbar',
          {content: 'Error loading interest groups: ' + error, color: 'error'}
        )
      } finally {
      }
    },
    changeSelectedGroups({commit}, groups) {
      commit('setSelectedGroups', {groups: groups})
    },

    async fetchInterestReportType ({dispatch}) {
        try {
          const response = await axios.get('/api/report-type/')
          for (let rt of response.data) {
            if (rt.short_name === 'interest') {
              return rt
            }
          }
        } catch (error) {
          dispatch(
            'showSnackbar',
            {content: 'Error loading report types: ' + error, color: 'error'}
          )
        }
        return null
      }
  },

  mutations: {
    setInterestGroups (state, {interestGroups}) {
      state.interestGroups = interestGroups
    },
    setSelectedGroups (state, {groups}) {
      state.selectedGroups = groups
    }
  }

}
