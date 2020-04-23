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
    async login(context, {email, password}) {
      context.commit('setLoginError', {'error': null})
      let csrftoken = Cookies.get('csrftoken')

      try {
        await axios.post(
          '/api/rest-auth/login/',
          {'email': email, 'password': password},
          {headers: {'X-CSRFToken': csrftoken}, privileged: true})

        this.commit('setAuthenticated', true)
        this.dispatch('setShowLoginDialog', false)
        this.dispatch('loadUserData')
        this.dispatch('afterAuthentication')
      } catch (error) {
        context.commit('setLoginError', {'error': error})
      }
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
