import Vue from 'vue'
import Vuex from 'vuex'
import axios from 'axios'
import Cookies from 'js-cookie'
import addMonths from 'date-fns/add_months'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    user: null,
    snackbarShow: false,
    snackbarContent: null,
    loginError: null,
    organizations: {},
    selectedOrganizationId: null,
    dateRangeStart: null,
    dateRangeEnd: null,
    dateRangeIndex: 0,
    dateRanges: [
          {name: 'date_range.all_available', start: null, end: null},
          {name: 'date_range.last_12_mo', start: -12, end: 0},
          {name: 'date_range.explicit', custom: true},
        ],
  },
  getters: {
    avatarImg: state => {
      return null
    },
    avatarText: state => {
      if (state.user) {
        return state.user.email[0].toUpperCase()
      }
      return 'A'
    },
    usernameText: state => {
      if (state.user) {
        return state.user.email
      }
      return 'not logged in'
    },
    loggedIn: state => state.user !== null,
    selectedOrganization: state => {
      if (state.organizations && state.selectedOrganizationId !== null) {
        return state.organizations[state.selectedOrganizationId]
      } else {
        return null
      }
    },
    selectedDateRange: state => state.dateRanges[state.dateRangeIndex],
  },
  actions: {
    start () {
      let that = this
      axios.interceptors.response.use(function (response) {
        // Do something with response data
        return response;
      }, function (error) {
        // Do something with response error
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          // if there is 40x error, try to reauthenticate
          that.dispatch('showSnackbar', {content: 'not logged in - you need to reauthenticate'})
        }
        return Promise.reject(error)
      })
      this.dispatch('loadUserData')
      this.dispatch('loadOrganizations')
      this.dispatch('changeDateRangeObject', {dateRangeIndex: 1})
    },
    showSnackbar(context, {content}) {
      context.commit('setSnackbarContent', {'content': content})
      context.commit('setSnackbarShow', {'show': true})
    },
    hideSnackbar(context) {
      context.commit('setSnackbarShow', {'show': false})
    },
    selectOrganization (context, {id}) {
      context.commit('setSelectedOrganizationId', {id})
    },
    loadUserData (context) {
      axios.get('/api/user/')
        .then(response => {
          context.commit('setUserData', response.data)
        })
        .catch(error => {
          context.dispatch('showSnackbar', {content: 'Error loading user data: '+error})
        })
    },
    loadOrganizations (context) {
      axios.get('/api/organization/')
        .then(response => {
          let organizations = {}
          for (let rec of response.data) {
            organizations[rec.pk] = rec
          }
          context.commit('setOrganizations', organizations)
          if (context.selectedOrganizationId === undefined && response.data.length > 0) {
            context.commit('setSelectedOrganizationId', {id: response.data[0].pk})
          }
        })
        .catch(error => {
          context.dispatch('showSnackbar', {content: 'Error loading organizations: '+error})
        })
    },
    changeDateRangeObject (context, {dateRangeIndex}) {
      let drObj = context.state.dateRanges[dateRangeIndex]
      let start = null
      let end = null
      if (!drObj.custom) {
        // for custom specified, we do not do anything with the start and end
        start = new Date()
        if (drObj.start) {
          start = addMonths(start, drObj.start)
        }
        end = new Date()
        if (drObj.end) {
          end = addMonths(end, drObj.end)
        }
      }
      context.commit('changeDateRange', {index: dateRangeIndex, start: start, end: end})
    }
  },
  mutations: {
    setSnackbarShow(state, {show}) {
      Vue.set(state, 'snackbarShow', show)
    },
    setSnackbarContent(state, {content}) {
      Vue.set(state, 'snackbarContent', content)
    },
    setLoginError(state, {error}) {
      Vue.set(state, 'loginError', error)
    },
    setAuthToken(state, {token}) {
      Vue.set(state, 'authToken', token)
    },
    setUserData(state, user) {
      state.user = user
    },
    setOrganizations(state, organizations) {
      state.organizations = organizations
    },
    setSelectedOrganizationId(state, {id}) {
      state.selectedOrganizationId = id
    },
    changeDateRange(state, {index, start, end}) {
      state.dateRangeIndex = index
      state.dateRangeStart = start
      state.dateRangeEnd = end
    }
  }
})
