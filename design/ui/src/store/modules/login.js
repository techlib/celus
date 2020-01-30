import axios from 'axios'

export default {

  state: {
    email: '',
    loginError: null,
    authenticated: false,
  },

  actions: {

    async login(context, {email, password}) {
      context.commit('setLoginError', {'error': null})
      let csrftoken = Cookies.get('csrftoken')

      try {
        let response = await axios.post(
          '/rest-auth/login/',
          {'email': email, 'password': password},
          {headers: {'X-CSRFToken': csrftoken}})

        this.commit('setAuthenticated', true)
      } catch (error) {
        context.commit('setLoginError', {'error': error})
      }
    },
  },

  mutations: {
    setLoginError(state, {error}) {
      Vue.set(state, 'loginError', error)
    },
    setAuthenticated(state, authenticated) {
      state.authenticated = authenticated
    }
  }
}
