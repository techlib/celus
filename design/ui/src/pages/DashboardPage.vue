<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <h3 v-text="$t('interest')"></h3>
                <APIChart
                        v-if="interestReportType"
                        :organization="organizationId"
                        primary-dimension="date"
                        :report-type-id="interestReportType.pk"
                        raw-report-type
                >
                </APIChart>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>

  import APIChart from '../components/APIChart'
  import {mapActions, mapState} from 'vuex'

  export default {
    name: "DashboardPage",

    components: {
      APIChart,
    },

    data () {
      return {
        interestReportType: null,
      }
    },

    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      }),
    },

    methods: {
      ...mapActions({
        fetchInterestReportType: 'fetchInterestReportType',
      }),
      async fetchReportTypes () {
        this.interestReportType = await this.fetchInterestReportType()
      }
    },

    mounted() {
      this.fetchReportTypes()
    }


  }
</script>

<style scoped>

</style>
