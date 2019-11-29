<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
    <v-container>
        <!--v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row-->
        <v-row>
            <v-col>
                <v-card>
                    <v-card-title v-text="$t('interest')"></v-card-title>
                    <v-card-text>
                        <APIChart
                                v-if="interestReportType"
                                :organization="organizationId"
                                primary-dimension="date"
                                :report-type-id="interestReportType.pk"
                                secondary-dimension="Interest_Type"
                                raw-report-type
                                stack
                        >
                        </APIChart>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
        <v-row>
            <v-col>

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
