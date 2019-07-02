<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-layout align-baseline>
        <v-flex class="sc" shrink mr-2>{{ $t('organization') }}:</v-flex>
        <v-flex>
            <v-select
                    v-model="orgId"
                    :items="items"
                    item-text="name"
                    item-value="pk"
                    class="short"
            >
            </v-select>
        </v-flex>
    </v-layout>
</template>
<script>
  import { mapActions, mapGetters, mapState } from 'vuex'

  export default {
    name: 'OrganizationSelector',
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      }),
      ...mapState({
        organizations: 'organizations',
        selectedOrganizationId: 'selectedOrganizationId'
      }),
      items () {
        if (!this.organizations) {
          return []
        }
        return Object.values(this.organizations)
      },
      orgId: {
        get () {
          return this.selectedOrganizationId
        },
        set (value) {
          this.selectOrganization({id: value})
        }
      }
    },
    methods: {
      ...mapActions({
        selectOrganization: 'selectOrganization',
      })
    },
    watch: {
      orgPK () {
        this.selectOrganization({pk: this.orgId})
      }
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
