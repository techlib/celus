<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  hide_successful: Hide successful rows
  stats: Statistics
  no_data_yet: No attempts were made for the selected month

cs:
  hide_successful: Skrýt úspěšné řádky
  stats: Statistika
  no_data_yet: Pro vybraný měsíc nebyla zatím stažena žádná data
</i18n>


<template>
    <v-card>
        <v-card-text>
            <v-container fluid>
                <v-row>
                    <v-col cols="auto">
                        <v-menu
                                v-model="showMonthMenu"
                                transition="scale-transition"
                                offset-y
                        >
                            <template v-slot:activator="{ on }">
                                <v-text-field
                                        v-model="selectedMonth"
                                        :label="$t('month')"
                                        prepend-icon="fa-calendar"
                                        readonly
                                        v-on="on"
                                >
                                    <template #prepend-inner>
                                        <IconButton @click="shiftMonth(-1)">fa-caret-left</IconButton>
                                    </template>
                                    <template #append>
                                        <IconButton @click="shiftMonth(1)">fa-caret-right</IconButton>
                                    </template>
                                </v-text-field>
                            </template>
                            <v-date-picker
                                    v-model="selectedMonth"
                                    type="month"
                                    no-title
                                    :locale="$i18n.locale"
                                    :allowed-dates="allowedMonths"
                            ></v-date-picker>
                        </v-menu>
                    </v-col>
                    <v-col cols="2">
                        <v-select
                                :items="[{text: '4 + 5', value: null}, {text: '4', value: 4}, {text: '5', value: 5}]"
                                v-model="counterVersion"
                                :label="$t('labels.counter_version')"
                                class="short"
                        ></v-select>
                    </v-col>
                    <v-col>
                        <v-select
                                :label="$t('platform')"
                                v-model="selectedPlatform"
                                :items="usedPlatforms"
                                item-value="pk"
                                item-text="name"
                        >
                        </v-select>
                    </v-col>
                    <v-col>
                        <v-switch
                                v-model="hideSuccessful"
                                :label="$t('hide_successful')"
                        >

                        </v-switch>
                    </v-col>
                </v-row>

                <v-row>
                    <v-col>
                        <div class="stats">
                            <h4 class="d-inline-block mr-5">{{ $t('stats') }}:</h4>
                            <span v-if="stateStats.length">
                                <span v-for="[state, count] in stateStats" class="mr-3" :key="state">
                                    <SushiAttemptStateIcon :force-state="state"/>
                                    {{ count }}
                                </span>
                            </span>
                            <span v-else v-text="$t('no_data_yet')"></span>
                        </div>
                    </v-col>
                </v-row>


                <v-row>
                    <v-data-table
                            :items="sushiCredentialsWithAttempts"
                            :headers="headers"
                            :search="search"
                            :items-per-page.sync="itemsPerPage"
                            :sort-by="orderBy"
                            multi-sort
                            :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
                            :loading="loading"
                            dense
                    >
                        <template v-for="rt in usedReportTypes" v-slot:[slotName(rt)]="{item}">
                            <span
                                    :key="`${rt.code}-${item.credentials_id}`"
                                    @click="showAttempt(item[rt.code])"
                            >
                                <SushiAttemptStateIcon :attempt="item[rt.code]" latest/>
                            </span>
                        </template>

                    </v-data-table>
                </v-row>
            </v-container>
        </v-card-text>

        <v-dialog v-model="showDetailsDialog">
            <SushiAttemptListWidget
                    v-if="selectedAttempt"
                    :attempt-id="selectedAttempt.pk"
                    @close="closeDetailsDialog"
            >
            </SushiAttemptListWidget>
        </v-dialog>
    </v-card>

</template>

<script>
import axios from 'axios'
import { mapActions, mapGetters } from 'vuex'
import debounce from 'lodash/debounce'
import SushiAttemptListWidget from '@/components/sushi/SushiAttemptListWidget'
import startOfMonth from 'date-fns/startOfMonth'
import addDays from 'date-fns/addDays'
import addMonths from 'date-fns/addMonths'
import { parseDateTime, ymDateFormat } from '@/libs/dates'
import SushiAttemptStateIcon from '@/components/sushi/SushiAttemptStateIcon'
import { attemptState } from '@/libs/attempt-state'
import IconButton from '@/components/sushi/IconButton'

export default {
    name: "SushiCredentialsMonthOverviewWidget",

    components: {IconButton, SushiAttemptStateIcon, SushiAttemptListWidget},

    props: {
      dialogMaxWidth: {
        required: false,
        default: '1000px',
      },
      organizationId: {
        default: -1,
        type: Number,
        required: false,
      },
    },

    data () {
      return {
        sushiCredentialsList: [],
        attemptData: [],
        attemptMap: new Map(),
        reportTypes: [],
        search: '',
        itemsPerPage: 25,
        selectedAttempt: null,
        showDetailsDialog: false,
        orderBy: ['platform.name', 'organization.name'],
        loading: false,
        selectedMonth: this.$route.query.month || ymDateFormat(addDays(startOfMonth(new Date()), -15)),
        showMonthMenu: false,
        counterVersion: null,
        hideSuccessful: false,
        selectedPlatform: null,
      }
    },
    computed: {
      ...mapGetters({
        consortialInstall: 'consortialInstall',
      }),
      headers () {
        let allHeaders = [
          {
            text: this.$i18n.t('title'),
            value: 'title',
            class: 'wrap',
          },
          {
            text: this.$i18n.t('platform'),
            value: 'platform.name'
          },
          {
            text: this.$i18n.t('organization'),
            value: 'organization.name',
            class: 'wrap',
          },
          {
            text: this.$i18n.t('title_fields.counter_version'),
            value: 'counter_version',
            align: 'end',
          },
        ]
        for (let reportType of this.usedReportTypes) {
          allHeaders.push({
            text: reportType.code,
            value: reportType.code,
            sortable: false,
          })
        }
        return allHeaders.filter(row => row.value !== 'outside_consortium' || this.consortialInstall)
      },
      searchDebounced: {
        get () {
          return this.search
        },
        set: debounce(function (value) {
          this.search = value
        }, 500)
      },
      credentialsUrl () {
        return `/api/sushi-credentials/?organization=${this.organizationId}`
      },
      attemptsUrl () {
        if (!this.selectedMonth) {
          return null
        }
        return `/api/sushi-credentials/month-overview/?organization=${this.organizationId}&month=${this.selectedMonth}`
      },
      usedReportTypes () {
        let usedRTIds = new Set()
        for (let cred of this.sushiCredentialsWithAttempts) {
          for (let rt of cred.active_counter_reports) {
            usedRTIds.add(rt)
          }
        }
        return this.reportTypes.filter(item => usedRTIds.has(item.id))
      },
      usedPlatforms () {
        let usedPlatforms = new Set(this.sushiCredentialsList
          .filter(item =>
            this.counterVersion === null || item.counter_version === this.counterVersion)
          .map(item => item.platform))
        return [{name: '-', pk: null}, ...usedPlatforms].sort((a, b) => a.name > b.name)
      },
      activeAttempts () {
        let attempts = []
        for (let cred of this.sushiCredentialsWithAttempts) {
          for (let rt of cred.active_counter_reports_long) {
            if (cred.hasOwnProperty(rt.code)) {
              attempts.push(cred[rt.code])
            }
          }
        }
        return attempts

        let activeCredentials = new Set(this.sushiCredentialsWithAttempts.map(item => item.pk))
        return this.attemptData.filter(item => activeCredentials.has(item.credentials_id))

      },
      sushiCredentialsWithAttempts () {
        return this.sushiCredentialsList
          .filter(item => item.enabled)
          .filter(item => this.counterVersion === null || item.counter_version === this.counterVersion)
          .filter(item => this.selectedPlatform === null || item.platform.pk === this.selectedPlatform)
          .map(item => {
            for (let reportType of item.active_counter_reports_long) {
              let key = `${item.pk}-${reportType.id}`
              if (this.attemptMap.has(key)) {
                item[reportType.code] = this.attemptMap.get(key)
              } else {
                item[reportType.code] = {untried: true}
              }
            }
            return item
          })
          .filter(item => !this.hideSuccessful || this.usedReportTypes.filter(rt => item[rt.code] && item[rt.code].import_batch).length != this.usedReportTypes.filter(rt => item[rt.code]).length)
      },
      stateStats () {
        let stats = new Map()
        for (let state of this.activeAttempts.map(attemptState)) {
          if (stats.has(state)) {
            stats.set(state, stats.get(state) + 1)
          } else {
            stats.set(state, 1)
          }
        }
        return [...stats.entries()]
      },
    },

    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadSushiCredentialsList () {
        this.loading = true
        try {
          let response = await axios.get(this.credentialsUrl)
          this.sushiCredentialsList = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading credentials list: '+error, color: 'error'})
        } finally {
          this.loading = false
        }
      },
      async loadAttempts () {
        if (!this.attemptsUrl) {
          return
        }
        this.loading = true
        try {
          let response = await axios.get(this.attemptsUrl)
          this.attemptData = response.data
          // create a map to easily find the attempt data
          let attemptMap = new Map()
          this.attemptData.forEach(item => attemptMap.set(`${item.credentials_id}-${item.counter_report_id}`, item))
          this.attemptMap = attemptMap
        } catch (error) {
          this.showSnackbar({content: 'Error loading attempts: '+error, color: 'error'})
        } finally {
          this.loading = false
        }
      },
      async loadReportTypes () {
        this.loading = true
        try {
          let response = await axios.get('/api/counter-report-type/')
          this.reportTypes = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading report types: '+error, color: 'error'})
        } finally {
          this.loading = false
        }
      },
      closeDetailsDialog () {
        this.selectedCredentials = null
        this.showDetailsDialog = false
      },
      allowedMonths (value) {
        let now = ymDateFormat(new Date())
        return value <= now
      },
      slotName: rt =>  'item.' + rt.code,
      showAttempt (attempt) {
        this.selectedAttempt = attempt
        this.showDetailsDialog = true
      },
      shiftMonth (months) {
        let date = parseDateTime(this.selectedMonth)
        this.selectedMonth = ymDateFormat(addMonths(date, months))
      },
    },

    watch: {
      selectedMonth () {
        history.pushState(
          {},
          null,
          this.$route.path + `?month=${this.selectedMonth}`
        )
      },
      dataUrl () {
        this.loadSushiCredentialsList()
      },
      attemptsUrl () {
        this.loadAttempts()
      }
    },

    mounted() {
      this.loadReportTypes()
      this.loadSushiCredentialsList()
      this.loadAttempts()
    }
  }
</script>

<style lang="scss" scoped>

div.stats {
  background-color: #efefef;
  padding: 0.5rem 1rem;
  border-radius: 5px;
}

</style>
