import Vue from 'vue'
import Vuex from 'vuex'
import axios from 'axios'
import Cookies from 'js-cookie'
import addMonths from 'date-fns/add_months'
import { ymDateFormat } from '../libs/dates'
import { format as formatNumber } from 'mathjs'

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
          {name: 'date_range.custom', custom: true},
        ],
    numberFormat: {
          notation: 'fixed',
          precision: 1,
    },
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
    dateRangeStartText (state) {
      if (state.dateRangeStart) {
        return ymDateFormat(state.dateRangeStart)
      }
      return ''
    },
    dateRangeEndText (state) {
      if (state.dateRangeEnd) {
        return ymDateFormat(state.dateRangeEnd)
      }
      return ''
    },
    formatNumber (state) {
      return (number) => (number === null) ? '-' : formatNumber(number, state.numberFormat)
    },
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
      this.dispatch('changeDateRangeObject', 1)
    },
    showSnackbar (context, {content}) {
      context.commit('setSnackbarContent', {'content': content})
      context.commit('setSnackbarShow', {'show': true})
    },
    hideSnackbar (context) {
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
          context.dispatch('showSnackbar', {content: 'Error loading user data: ' + error})
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
          context.dispatch('showSnackbar', {content: 'Error loading organizations: ' + error})
        })
    },
    changeDateRangeObject (context, dateRangeIndex) {
      let drObj = context.state.dateRanges[dateRangeIndex]
      let start = null
      let end = null
      if (!drObj.custom) {
        // for custom specified, we do not do anything with the start and end
        if (drObj.start !== null) {
          start = addMonths(new Date(), drObj.start)
        }
        if (drObj.end !== null) {
          end = addMonths(new Date(), drObj.end)
        }
        context.commit('changeDateRange', {index: dateRangeIndex, start: start, end: end})
      } else {
        context.commit('changeDateRange', {index: dateRangeIndex})
        // if the end of the period is not specified, set it to current data,
        // because 'undefined' and null states are both used for special purposes
        // in the changeDateRange, we use the specific setters here
        if (context.state.dateRangeEnd === null) {
          context.commit('setDateRangeEnd', {date: new Date()})
        }
        if (context.state.dateRangeStart === null) {
          context.commit('setDateRangeStart', {date: addMonths(context.state.dateRangeEnd, -24)})
        }
      }
    },
    changeDateRangeStart (context, date) {
      context.commit('setDateRangeStart', {date})
    },
    changeDateRangeEnd (context, date) {
      context.commit('setDateRangeEnd', {date})
    },
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
      if (typeof start !== 'undefined') {
        state.dateRangeStart = start
      }
      if (typeof end !== 'undefined') {
        state.dateRangeEnd = end
      }
    },
    setDateRangeStart(state, {date}) {
      state.dateRangeStart = date
    },
    setDateRangeEnd(state, {date}) {
      state.dateRangeEnd = date
    },
  }
})
