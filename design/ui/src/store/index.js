import Vue from 'vue'
import Vuex from 'vuex'
import axios from 'axios'
import Cookies from 'js-cookie'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    user: null,
    snackbarShow: false,
    snackbarContent: null,
    loginError: null,
    organizations: null,
    selectedOrganizationIndex: null,
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
      if (state.organizations && state.selectedOrganizationIndex !== null) {
        return state.organizations[state.selectedOrganizationIndex]
      } else {
        return null
      }
    }
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
    },
    showSnackbar(context, {content}) {
      context.commit('setSnackbarContent', {'content': content})
      context.commit('setSnackbarShow', {'show': true})
    },
    hideSnackbar(context) {
      context.commit('setSnackbarShow', {'show': false})
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
          context.commit('setOrganizations', response.data)
          if (context.selectedOrganizationIndex === undefined && response.data.length > 0) {
            context.commit('setSelectedOrganizationIndex', {index: 0})
          }
        })
        .catch(error => {
          context.dispatch('showSnackbar', {content: 'Error loading organizations: '+error})
        })
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
    setSelectedOrganizationIndex(state, {index}) {
      state.selectedOrganizationIndex = index
    }
  }
})
