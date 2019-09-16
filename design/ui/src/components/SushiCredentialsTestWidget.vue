<template>
    <v-container>
        <v-row>
            <v-col>
                <v-date-picker
                        v-model="startDate"
                        type="month"
                        no-title
                        :locale="$i18n.locale"
                        :allowed-dates="allowedStartMonths"
                ></v-date-picker>
            </v-col>
            <v-col>
                <v-date-picker
                        v-model="endDate"
                        type="month"
                        no-title
                        :locale="$i18n.locale"
                        :allowed-dates="allowedEndMonths"
                ></v-date-picker>
            </v-col>
        </v-row>
        <v-row v-if="!started">
            <v-col>
                <v-btn @click="createAttempts()" v-text="$t('start_test')"></v-btn>
            </v-col>
        </v-row>
        <v-row v-else no-gutters>
            <v-col v-for="attemptId in attemptIds" :key="attemptId" cols="12">
                <SushiCredentialsStatusWidget
                        :attempt-id="attemptId"
                        :key="attemptId"
                        ref="attemptStatus"
                >
                </SushiCredentialsStatusWidget>

            </v-col>

        </v-row>
    </v-container>
</template>

<script>
  import { mapActions } from 'vuex'
  import axios from 'axios'
  import { ymDateFormat } from '../libs/dates'
  import SushiCredentialsStatusWidget from './SushiCredentialsStatusWidget'
  import addMonths from 'date-fns/add_months'

  export default {
    name: 'SushiCredentialsTestWidget',
    components: {SushiCredentialsStatusWidget},
    props: {
      credentials: {required: true, type: Object},
      reportTypes: {required: true, type: Array},
    },
    data () {
      return {
        attemptIds: [], //11757, 11758],
        startDate: null,
        endDate: null,
        started: false,
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async createAttempts () {
        for (let rt of this.reportTypes) {
          this.createAttempt(rt)
        }
        this.started = true
      },
      async createAttempt (reportType) {
        try {
          let response = await axios.post(
            `/api/sushi-fetch-attempt/`,
            {
              start_date: this.startDate + '-01',
              end_date: this.endDate + '-01',
              credentials: this.credentials.id,
              counter_report: reportType,
            }
          )
          this.attemptIds.push(response.data.pk)
        } catch (error) {
          this.showSnackbar({content: 'Error starting SUSHI test: ' + error, color: 'error'})
        }
      },
      allowedStartMonths (value) {
        let end = this.endDate
        if (end) {
          return value <= end
        }
        return value <= ymDateFormat(new Date())
      },
      allowedEndMonths (value) {
        let now = ymDateFormat(new Date())
        let start = this.startDate
        if (start) {
          return (start <= value) && (value <= now)
        }
        return value <= now
      },
      clean () {
        this.started = false
        for (let comp of this.$refs.attemptStatus) {
          comp.stop()
        }
        this.attemptIds = []
      }
    },
    mounted () {
      if (this.startDate === null) {
        this.startDate = ymDateFormat(addMonths(new Date(), -1))
      }
      if (this.endDate === null) {
        this.endDate = this.startDate
      }
    }
  }
</script>

<style scoped>

</style>
