<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
    sushi_fetch_attempts: Sushi fetch attempts
    timestamp: Time of attempt
    show_success: Show successful
    show_failure: Show failures
    show_raw_data: Show raw data
    show_chart: Show charts
    not_older_than: Not older than
    counter_version: Counter version

cs:
    sushi_fetch_attempts: Pokusy o stažení Sushi
    timestamp: Čas pokusu
    show_success: Zobrazit úspěšné
    show_failure: Zobrazit neúspěšné
    show_raw_data: Zobrazit data
    show_chart: Zobrazit grafy
    not_older_than: Ne starší než
    counter_version: Verze Counter
</i18n>

<template>
    <v-card>
        <v-card-title>{{ $t('sushi_fetch_attempts') }}</v-card-title>
        <v-card-text>
            <v-container fluid>
                <v-row>
                    <v-col cols="12" md="6" lg="5">
                        <table class="overview">
                            <tr v-if="organization">
                                <th class="text-left">{{ $t('organization') }}:</th>
                                <td>{{ organization.name }}</td>
                            </tr>
                            <tr v-if="platform">
                                <th class="text-left">{{ $t('platform') }}:</th>
                                <td>{{ platform.name }}</td>
                            </tr>
                            <tr v-if="report">
                                <th class="text-left">{{ $t('labels.report_type') }}:</th>
                                <td>{{ report.name }}</td>
                            </tr>
                            <tr v-if="counterVersion">
                                <th class="text-left">{{ $t('labels.counter_version') }}:</th>
                                <td>{{ counterVersion }}</td>
                            </tr>
                            <tr v-if="month">
                                <th class="text-left">{{ $t('month') }}:</th>
                                <td>{{ month.name }}</td>
                            </tr>
                            <tr v-if="fromDate">
                                <th class="text-left">{{ $t('not_older_than') }}:</th>
                                <td>{{ fromDate }}</td>
                            </tr>
                        </table>
                    </v-col>
                    <v-spacer></v-spacer>
                    <v-col cols="12" lg="7">
                        <v-container fluid class="pa-0">
                            <v-row justify="end">
                                <v-col cols="auto" class="py-0">
                                    <FetchAttemptModeFilter v-model="historyMode"/>
                                </v-col>
                                <v-col cols="auto" class="py-0">
                                    <v-switch v-model="showSuccess" :label="$t('show_success')" color="success" dense></v-switch>
                                </v-col>
                                <v-col cols="auto" class="py-0">
                                    <v-switch v-model="showFailure" :label="$t('show_failure')" color="error" dense></v-switch>
                                </v-col>
                            </v-row>
                        </v-container>
                    </v-col>
                </v-row>
                <v-row>
                    <v-col>
                        <v-data-table
                                :items="filteredAttempts"
                                :headers="headers"
                                show-expand
                                :expanded.sync="expandedRows"
                                item-key="timestamp"
                                :sort-by="orderBy"
                                :sort-desc="orderDesc"
                                :items-per-page="5"
                                :loading="loading"
                        >
                            <template v-slot:item.download_success="props">
                                <CheckMark :value="props.item.download_success" />
                            </template>
                            <template v-slot:item.processing_success="props">
                                <CheckMark :value="props.item.processing_success" />
                            </template>
                            <template v-slot:item.contains_data="props">
                                <CheckMark :value="props.item.contains_data" />
                            </template>
                            <template v-slot:item.is_processed="props">
                                <CheckMark :value="props.item.is_processed" />
                            </template>
                            <template v-slot:expanded-item="{item, headers}">
                                <th colspan="2">Log</th>
                                <td :colspan="headers.length-3" class="pre">{{ item.log }}</td>
                                <td v-if="item.data_file"><a :href="item.data_file" target="_blank">Data file</a></td>
                            </template>
                            <template v-slot:item.data-table-expand="{isExpanded, expand}">
                                <v-icon @click="expand(!isExpanded)" small>{{ isExpanded  ? 'fa-angle-down' : 'fa-angle-right' }}</v-icon>
                            </template>
                            <template v-slot:item.actions="{item}">
                                <v-tooltip bottom v-if="item.import_batch">
                                    <template v-slot:activator="{ on }">
                                        <v-btn text small color="secondary" @click.stop="selectedBatch = item.import_batch; dialogType = 'data'; showBatchDialog = true" v-on="on">
                                            <v-icon left small>fa-microscope</v-icon>
                                        </v-btn>
                                    </template>
                                    <span>{{ $t('show_raw_data') }}</span>
                                </v-tooltip>
                                <v-tooltip bottom v-if="item.import_batch">
                                    <template v-slot:activator="{ on }">
                                        <v-btn text small color="secondary" @click.stop="selectedBatch = item.import_batch; dialogType = 'chart'; showBatchDialog = true" v-on="on">
                                            <v-icon left small>fa-chart-bar</v-icon>
                                        </v-btn>
                                    </template>
                                    <span>{{ $t('show_chart') }}</span>
                                </v-tooltip>
                            </template>
                        </v-data-table>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-text>
        <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="$emit('close')">{{ $t('close') }}</v-btn>
        </v-card-actions>

        <v-dialog
                v-model="showBatchDialog"
        >
            <v-card>
                <v-card-text>
                    <AccessLogList v-if="dialogType === 'data'" :import-batch="selectedBatch" />
                    <ImportBatchChart v-else-if="dialogType === 'chart'" :import-batch-id="selectedBatch" />
                </v-card-text>
                <v-card-actions>
                    <v-layout pb-3 pr-5 justify-end>
                        <v-btn @click="showBatchDialog = false">{{ $t('actions.close') }}</v-btn>
                    </v-layout>
                </v-card-actions>
            </v-card>
    </v-dialog>
    </v-card>
</template>

<script>
  import { mapActions } from 'vuex'
  import axios from 'axios'
  import AccessLogList from './AccessLogList'
  import ImportBatchChart from './ImportBatchChart'
  import CheckMark from './CheckMark'
  import FetchAttemptModeFilter from './sushi/FetchAttemptModeFilter'

  export default {
    name: "SushiAttemptListWidget",
    components: {AccessLogList, ImportBatchChart, CheckMark, FetchAttemptModeFilter},
    props: {
      organization: {required: false},
      platform: {required: false},
      report: {required: false},
      fromDate: {required: false},
      month: {required: false},
      counterVersion: {required: false},
    },
    data () {
      return {
        attempts: [],
        expandedRows: [],
        showSuccess: true,
        showFailure: true,
        orderBy: 'timestamp',
        orderDesc: true,
        showBatchDialog: false,
        selectedBatch: null,
        dialogType: '',
        loading: false,
        hideObsolete: true,
        historyMode: 'success_and_current'
      }
    },
    computed: {
      listUrl () {
        if (!(this.organization || this.platform || this.report)) {
          return ''
        }
        let base = `/api/sushi-fetch-attempt/?format=json&mode=${this.historyMode}`
        if (this.organization) {
          base += `&organization=${this.organization.pk}`
        }
        if (this.platform) {
          base += `&platform=${this.platform.pk}`
        }
        if (this.report) {
          base += `&report=${this.report.pk}`
        }
        if (this.fromDate) {
          base += `&date_from=${this.fromDate}`
        }
        if (this.month) {
          base += `&month=${this.month.pk}`
        }
        if (this.counterVersion) {
          base += `&counter_version=${this.counterVersion}`
        }
        return base
      },
      headers () {
        let ret = [
          {
            text: this.$t('title_fields.download_success'),
            value: 'download_success'
          },
          {
            text: this.$t('title_fields.processing_success'),
            value: 'processing_success'
          },
          {
            text: this.$t('title_fields.contains_data'),
            value: 'contains_data'
          },
          {
            text: this.$t('title_fields.processed'),
            value: 'is_processed'
          },
          {
            text: this.$t('timestamp'),
            value: 'timestamp'
          },
          {
            text: this.$t('title_fields.start_date'),
            value: 'start_date'
          },
          {
            text: this.$t('title_fields.end_date'),
            value: 'end_date'
          },
          {
            text: this.$t('title_fields.error_code'),
            value: 'error_code'
          },
        ]
        if (!this.organization) {
          ret.push({text: this.$t('organization'), value: 'organization.name'})
        }
        if (!this.report) {
          ret.push({text: this.$t('report'), value: 'counter_report_verbose.code'})
        }
        ret.push({text: this.$t('title_fields.actions'), value: 'actions'})

        return ret
      },
      filteredAttempts () {
        let out = this.attempts
        if (!this.showSuccess) {
          out = out.filter(item => !item.processing_success)
        }
        if (!this.showFailure) {
          out = out.filter(item => item.processing_success)
        }
        return out
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadAttempts () {
        if (!this.listUrl) {
          return
        }
        this.loading = true
        this.attempts = []
        try {
          let response = await axios.get(this.listUrl)
          this.attempts = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error fetching SUSHI attempt data: ' + error, color: 'error'})
        } finally {
          this.loading = false
        }
      },
    },
    watch: {
      listUrl () {
        this.loadAttempts()
      }
    },
    mounted() {
      this.loadAttempts()
    }
  }
</script>

<style scoped lang="scss">

    table.overview {
        th {
            padding-right: 1rem;
        }
    }

    td.pre {
        font-family: Courier, monospace;
        color: #666666;
        white-space: pre-wrap;
    }
</style>
