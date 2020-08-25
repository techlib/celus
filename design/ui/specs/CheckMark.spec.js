// basic imports
import Vue from 'vue'
import Vuetify from 'vuetify'
import { mount, createLocalVue } from '@vue/test-utils'

// stuff to check
import CheckMark from '@/components/util/CheckMark'

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
  test('check error color', () => {
    const wrapper = mount(CheckMark, {
      localVue,
      vuetify,
      propsData: {
        value: false,
      }
    })
    expect(wrapper.html()).toContain('error')
  }),

  test('check success color', () => {
    const wrapper = mount(CheckMark, {
      localVue,
      vuetify,
      propsData: {
        value: true,
      }
    })
    //wrapper.setProps({value: true})
    expect(wrapper.html()).toContain('success')
    expect(wrapper.html()).not.toContain('error')
  })

})
