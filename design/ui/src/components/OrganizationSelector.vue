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
            </v-autocomplete>
        </v-flex>
    </v-layout>
</template>
<script>
  import { mapActions, mapGetters, mapState } from 'vuex'

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
        if (this.user && this.user.is_from_master_organization) {
          out.push({name: 'All', name_cs: 'Všechny', name_en: 'All', pk: -1})
        }
        let loc_name = this.lang ? `name_${this.lang}` : 'name'
        out.sort((a, b) => ((a[loc_name] ? a[loc_name] : a['name']).localeCompare((b[loc_name] ? b[loc_name] : b['name']))))
        return out
      },
      orgId: {
        get () {
          return this.selectedOrganizationId
        },
        set (value) {
          this.selectOrganization({id: value})
          this.$router.push({name: 'platform-list'})
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

</style>
