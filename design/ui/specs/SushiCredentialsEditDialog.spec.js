// basic imports
import Vue from 'vue'
import Vuetify from 'vuetify'
import { mount, createLocalVue } from '@vue/test-utils'

// stuff to check
import SushiCredentialsEditDialog from '@/components/SushiCredentialsEditDialog'

// basic setup
Vue.use(Vuetify)
const localVue = createLocalVue()

describe('CheckMark', () => {

  // vuetify setup before each test
  let vuetify
  beforeEach(() => {
    vuetify = new Vuetify()
  })

  // the tests themselves
  test('check validity', () => {
    const wrapper = mount(SushiCredentialsEditDialog, {
      localVue,
      vuetify,
      propsData: {
      }
    })
    wrapper.setData({
      organizationId: 1,
      counterVersion: 5,
      customerId: 'cusid',
    })
    expect(wrapper.vm.valid).toBeFalsy()

  })

})
