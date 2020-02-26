<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
    select_dates_text: Select date range for SUSHI credentials test. A shorter period usually takes
                       less time to process, so using only one month is advisable.

cs:
    select_dates_text: Vyberte rozsah měsíců pro test přihlašovacích údajů. Kratší období je většinou
                       rychleji zpracováno, takže je vhodné vybrat jen jeden měsíc.
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>{{ $t('select_dates_text') }}</v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-menu
                        v-model="startDateMenu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        min-width="290px"
                >
                    <template v-slot:activator="{ on }">
                        <v-text-field
                                v-model="startDate"
                                :label="$t('title_fields.start_date')"
                                prepend-icon="fa-calendar"
                                readonly
                                v-on="on"
                        ></v-text-field>
                    </template>
                    <v-date-picker
                            v-model="startDate"
                            type="month"
                            no-title
                            :locale="$i18n.locale"
                            :allowed-dates="allowedStartMonths"
                    ></v-date-picker>
                </v-menu>
            </v-col>
            <v-col>
                <v-menu
                        v-model="endDateMenu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        min-width="290px"
                >
                    <template v-slot:activator="{ on }">
                        <v-text-field
                                v-model="endDate"
                                :label="$t('title_fields.end_date')"
                                prepend-icon="fa-calendar"
                                readonly
                                v-on="on"
                        ></v-text-field>
                    </template>
                    <v-date-picker
                            v-model="endDate"
                            type="month"
                            no-title
                            :locale="$i18n.locale"
                            :allowed-dates="allowedEndMonths"
                    ></v-date-picker>
                </v-menu>
            </v-col>
        </v-row>
        <v-row v-if="!started">
            <v-col>
                <v-btn @click="createAttempts()" v-text="$t('actions.start_test')"></v-btn>
            </v-col>
        </v-row>
        <v-row v-else no-gutters>
            <v-expansion-panels>
                <SushiCredentialsStatusWidget
                        v-for="attemptId in attemptIds"
                        :attempt-id="attemptId"
                        :key="attemptId"
                        ref="attemptStatus"
                >
                </SushiCredentialsStatusWidget>
            </v-expansion-panels>

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
        startDateMenu: null,
        endDateMenu: null,
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
              credentials: this.credentials.pk,
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
        if (this.$refs.attemptStatus) {
          for (let comp of this.$refs.attemptStatus) {
            comp.stop()
          }
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
