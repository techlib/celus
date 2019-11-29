<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
    <v-layout align-baseline>
        <v-flex class="sc" shrink mr-2>{{ $t('organization') }}:</v-flex>
        <v-flex>
            <v-autocomplete
                    v-model="orgId"
                    :items="items"
                    item-text="name"
                    item-value="pk"
                    clearable
                    eager
                    :menu-props="{width: '800px'}"
                    :filter="filter"
            >
                <template v-slot:item="{item}">
                    <span :class="{bold: item.extra, org: true}" v-text="item.name"></span>
                </template>
            </v-autocomplete>
        </v-flex>
    </v-layout>
</template>
<script>
  import {mapActions, mapGetters, mapState} from 'vuex'

  export default {
    name: 'OrganizationSelector',
    props: {
      'lang': {required: false, default: null},
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        items: 'organizationItems',
      }),
      orgId: {
        get () {
          return this.selectedOrganizationId
        },
        set (value) {
          this.selectOrganization({id: value})
          this.$router.push({name: 'home'}).catch(() => {}) // catch but ignore -
          // it is harmless (https://github.com/vuejs/vue-router/issues/2873)
        }
      }
    },
    methods: {
      ...mapActions({
        selectOrganization: 'selectOrganization',
      }),
      filter (item, queryText) {
        const words = queryText.toLowerCase().split(/ /)
        for (let word of words) {
          if (item.name.toLowerCase().indexOf(word) < 0)
            return false
        }
        return true
      }
    },
    watch: {
    }
  }
</script>
<style lang="scss">

    .sc {
        font-variant: small-caps;
    }

    .v-select.v-text-field.short input {
        max-width: 0;
    }

    .bold {
        font-weight: bold;
    }

    span.org {
        min-width: 600px;
    }
</style>
