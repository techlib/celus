<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  hide_successful: Hide successful rows
  stats: Statistics

cs:
  hide_successful: Skrýt úspěšné řádky
  stats: Statistika
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
                                ></v-text-field>
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
                        <span v-for="[state, count] in stateStats" class="mr-3" :key="state">
                            <SushiAttemptStateIcon :force-state="state"/>
                            {{ count }}
                        </span>
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
                                <SushiAttemptStateIcon :attempt="item[rt.code]"/>
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
import CheckMark from '@/components/CheckMark'
import startOfMonth from 'date-fns/startOfMonth'
import addDays from 'date-fns/addDays'
import { ymDateFormat } from '@/libs/dates'
import SushiAttemptStateIcon from '@/components/sushi/SushiAttemptStateIcon'
import { ATTEMPT_ERROR, ATTEMPT_SUCCESS, attemptState } from '@/libs/attempt-state'

export default {
    name: "SushiCredentialsMonthOverviewWidget",

    components: {SushiAttemptStateIcon, SushiAttemptListWidget, CheckMark},

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
      platformId: {
        default: null,
        type: Number,
        required: false,
      }
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
        selectedMonth: ymDateFormat(addDays(startOfMonth(new Date()), -15)),
        showMonthMenu: false,
        counterVersion: null,
        hideSuccessful: false,
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
          /*{
            text: this.$i18n.t('title_fields.outside_consortium'),
            value: 'outside_consortium',
          },
          {
            text: this.$i18n.t('title_fields.enabled'),
            value: 'enabled',
          },*/
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
        let base = `/api/sushi-credentials/?organization=${this.organizationId}`
        if (this.platformId) {
          base += `&platform=${this.platformId}`
        }
        return base
      },
      attemptsUrl () {
        if (!this.selectedMonth) {
          return null
        }
        let base = `/api/sushi-credentials/month-overview/?organization=${this.organizationId}&month=${this.selectedMonth}`
        if (this.platformId) {
          base += `&platform=${this.platformId}`
        }
        return base
      },
      usedReportTypes () {
        let usedRTIds = new Set(this.attemptData
          .filter(item =>
            this.counterVersion === null || item.counter_version === this.counterVersion)
          .map(item => item.counter_report_id))
        return this.reportTypes.filter(item => usedRTIds.has(item.id))
      },
      activeAttempts () {
        return this.attemptData.filter(item => this.counterVersion === null || item.counter_version === this.counterVersion)
      },
      sushiCredentialsWithAttempts () {
        return this.sushiCredentialsList.map(item => {
          for (let reportType of this.usedReportTypes) {
            item[reportType.code] = this.attemptMap.get(`${item.pk}-${reportType.id}`)
          }
          return item
        })
          .filter(item => this.counterVersion === null || item.counter_version === this.counterVersion)
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
      }

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
      }
    },

    watch: {
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
