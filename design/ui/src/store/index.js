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
    username: null,
    loginError: null,
    email: null,
    selectedOrganization: {'name': 'TEST'},
  },
  getters: {
    avatarImg: state => {
      return null
    },
    avatarText: state => {
      if (state.email !== null) {
        return state.email[0].toUpperCase()
      }
      return 'A'
    },
    usernameText: state => {
      if (state.email) {
        return state.email
      }
      return 'not logged in'
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
          console.log('reauthenticating', error.request)
          that.dispatch('setAuthToken', {'token': null})
        }
        return Promise.reject(error);
      });
    },
    showSnackbar(context, {content}) {
      context.commit('setSnackbarContent', {'content': content})
      context.commit('setSnackbarShow', {'show': true})
    },
    hideSnackbar(context) {
      context.commit('setSnackbarShow', {'show': false})
    },
    login(context, {email, password}) {
      context.commit('setLoginError', {'error': null})
      let csrftoken = Cookies.get('csrftoken')
      axios.post(
        '/rest-auth/login/',
        {'email': email, 'password': password},
        {headers: {'X-CSRFToken': csrftoken}})
        .then((response) => {
          let token = response.data.key
          this.commit('setEmail', {'email': email})
          this.dispatch('setAuthToken', {'token': token})
          this.dispatch('loadUserData')
          this.dispatch('loadWorksets')
        })
        .catch((error) => {
          console.log(error.response)
          context.commit('setLoginError', {'error': error})
        })
    },
    setAuthToken (context, {token}) {
      context.commit('setAuthToken', {'token': token})
      if (token) {
        Cookies.set('authtoken', token)
        axios.defaults.headers.common['Authorization'] = 'Token ' + token
      } else {
        Cookies.remove('authtoken')
        delete axios.defaults.headers.common['Authorization']
      }
    },
    loadUserData (context) {
      if (this.state.authToken) {
        axios.get('/rest-auth/user/')
          .then(response => {
            context.commit('setUserData', response.data)
          })
          .catch(error => {
            console.log('Error: '+error)
          })
      }
    }
  },
  mutations: {
    setSnackbarShow(state, {show}) {
      Vue.set(state, 'snackbarShow', show)
    },
    setSnackbarContent(state, {content}) {
      Vue.set(state, 'snackbarContent', content)
    },
    setUsername(state, {username}) {
      Vue.set(state, 'username', username)
    },
    setEmail(state, {email}) {
      Vue.set(state, 'email', email)
    },
    setLoginError(state, {error}) {
      Vue.set(state, 'loginError', error)
    },
    setAuthToken(state, {token}) {
      Vue.set(state, 'authToken', token)
    },
    setUserData(state, {pk, username, email, first_name, last_name}) {
      state.username = username
      state.email = email
    },
    setSelectedOrganization(state, {organization}) {
      state.selectedOrganization = organization
    }
  }
})
