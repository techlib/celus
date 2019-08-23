<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-layout align-baseline>
        <v-flex class="sc" shrink mr-2>{{ $t('organization') }}:</v-flex>
        <v-flex>
            <v-autocomplete
                    v-model="orgId"
                    :items="items"
                    :item-text="lang ? 'name_'+lang : 'name'"
                    item-value="pk"
            >
                <template v-slot:item="props">
                    <span :class="{bold: props.item.extra}">{{ lang ? props.item['name_'+lang] : props.item['name'] }}</span>
                </template>
            </v-autocomplete>
        </v-flex>
    </v-layout>
</template>
<script>
  import { mapActions, mapState } from 'vuex'

  export default {
    name: 'OrganizationSelector',
    props: {
      'lang': {required: false, default: null},
    },
    computed: {
      ...mapState({
        organizations: 'organizations',
        selectedOrganizationId: 'selectedOrganizationId',
        user: 'user',
      }),
      items () {
        if (!this.organizations) {
          return []
        }
        let out = Object.values(this.organizations)
        if (out.length === 0)
          return []
        let loc_name = this.lang ? `name_${this.lang}` : 'name'
        out.sort((a, b) => {
          if ('extra' in a) {
            return -1
          }
          if ('extra' in b) {
            return 1
          }
          return ((a[loc_name] ? a[loc_name] : a['name']).localeCompare((b[loc_name] ? b[loc_name] : b['name'])))
        })
        return out
      },
      orgId: {
        get () {
          return this.selectedOrganizationId
        },
        set (value) {
          this.selectOrganization({id: value})
          this.$router.push({name: 'platform-list'}).catch(() => {}) // catch but ignore -
          // it is harmless (https://github.com/vuejs/vue-router/issues/2873)
        }
      }
    },
    methods: {
      ...mapActions({
        selectOrganization: 'selectOrganization',
      })
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
</style>
