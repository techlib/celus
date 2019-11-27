// basic imports
import Vue from 'vue'
import Vuetify from 'vuetify'
import { mount, createLocalVue } from '@vue/test-utils'

// stuff to check
import CheckMark from '@/components/CheckMark'

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
  test('check color', () => {
    const wrapper = mount(CheckMark, {
      localVue,
      vuetify,
      propsData: {
        value: false,
      }
    })
    expect(wrapper.html()).toContain('error')
    wrapper.setProps({value: true})
    expect(wrapper.html()).not.toContain('error')
    expect(wrapper.html()).toContain('success')
  })

})
