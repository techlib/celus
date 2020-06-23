import axios from 'axios'
import Cookies from 'js-cookie'

export default {

  state: {
    email: '',
    loginError: null,
    authenticated: false,
    usesPasswordLogin: false,
  },

  getters: {
    loginErrorText (state) {
      if (state.loginError) {
        if (state.loginError.response.data) {
          if ('non_field_errors' in state.loginError.response.data) {
            return state.loginError.response.data.non_field_errors[0]
          }
        }
        return state.loginError
      }
      return null
    }
  },

  actions: {
    async login({commit, dispatch}, {email, password}) {
      commit('setLoginError', {'error': null})
      let csrftoken = Cookies.get('csrftoken')

      try {
        await axios.post(
          '/api/rest-auth/login/',
          {'email': email, 'password': password},
          {headers: {'X-CSRFToken': csrftoken}, privileged: true})

        commit('setAuthenticated', true)
        dispatch('setShowLoginDialog', false)
        dispatch('loadUserData')
        dispatch('afterAuthentication')
      } catch (error) {
        context.commit('setLoginError', {'error': error})
      }
    },
    async logout ({commit, dispatch}) {
      let csrftoken = Cookies.get('csrftoken')
      try {
        await axios.post(
          '/api/rest-auth/logout/',
          {},
          {headers: {'X-CSRFToken': csrftoken}})
      } catch (error) {
        dispatch('showSnackbar', {'content': 'Error logging out:' + error, color: 'error'})
        return
      }
      await dispatch('cleanUserData')
      await dispatch('setShowLoginDialog', {show: true})
    },
    changeUsesPasswordLogin({commit}, value) {
      commit('setUsesPasswordLogin', value)
    }
  },

  mutations: {
    setLoginError(state, {error}) {
      state.loginError = error
    },
    setAuthenticated(state, authenticated) {
      state.authenticated = authenticated
    },
    setUsesPasswordLogin(state, uses) {
      state.usesPasswordLogin = uses
    }

  }
}
