<i18n>
en:
    has_data: Has data
    platform: Platform

cs:
    has_data: Má data
    platform: Platforma
</i18n>

<template>
    <v-data-table
            :headers="headers"
            :items="platforms"
            :loading="loading"
            dense
            :items-per-page="-1"
            sort-by="has_data"
            :sort-desc="true"
            :hide-default-footer="true"
    >
        <template v-slot:item.name="{item}">
            <span v-text="item.name" :class="{bold: item.has_data}"></span>
        </template>
        <template v-slot:item.has_data="{item}">
            <CheckMark :value="item.has_data" true-color="warning" false-color="grey" />
        </template>
    </v-data-table>
</template>

<script>
  import { mapActions, mapState } from 'vuex'
  import CheckMark from './CheckMark'

  export default {
    name: 'UndefinedInterestWidget',
    components: {
      CheckMark,
    },
    data () {
      return {
        platforms: [],
        loading: false,
      }
    },
    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      }),
      headers () {
        return [
          {
            text: this.$t('platform'),
            value: 'name',
          },
          {
            text: this.$t('has_data'),
            value: 'has_data',
          }
        ]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
        fetchNoInterestPlatforms: 'fetchNoInterestPlatforms',
      }),
      async fetchPlatforms () {
        if (this.organizationId) {
          this.loading = true
          this.platforms = await this.fetchNoInterestPlatforms()
          this.loading = false
        }
      }
    },
    mounted () {
      this.fetchPlatforms()
    },
  }
</script>

<style scoped>
    span.bold {font-weight: bold}
</style>
