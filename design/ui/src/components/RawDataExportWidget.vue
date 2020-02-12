<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n>
en:
    export_raw_data: Export raw data
    info_text: It is possible to export all data related to this platform here. The
               amount of data is potentially quite huge, so the data is exported in CSV format
               inside a ZIP archive.
    record_count: Number of records to export
    error: There was an error exporting the data
    download_data: Download data
    preparing: Initializing export
    calculating: Calculating
    start_export: Start export
    export_running: Export is running, please wait.
    data_ready: Data is ready.

cs:
    export_raw_data: Export všech dat
    info_text: Zde je možné vyexportovat veškerá data k této platformě. Množství těchto
               dat může být potenciálně obrovské a data jsou proto exportována to formátu CSV
               zabaleného do ZIP archivu.
    record_count: Počet záznamů k exportu
    error: Během exportu došlo k neznámé chybě
    download_data: Stáhnout data
    preparing: Inicializuji export
    calculating: Počítám
    start_export: Spustit export
    export_running: Probíhá export, vydržte prosím.
    data_ready: Data jsou připravena.

</i18n>

<template>
    <span>
        <v-btn
                @click="showDialog = true"
                color="primary"
        >
            <v-icon left>fa-download</v-icon>
            {{ $t('export_raw_data') }}
        </v-btn>
        <v-dialog
                v-model="showDialog"
                max-width="600"
        >
            <v-card>
                <v-card-title>{{ $t('export_raw_data') }}</v-card-title>
                <v-card-text>
                    <div class="py-2">{{ $t('info_text') }}</div>
                    <div class="py-2">
                        <strong>{{ $t('record_count') }}</strong>:
                        <span v-if="loadingCount"><span class="fa fa-spin fa-spinner"></span> {{ $t('calculating') }}</span>
                        <span v-else>{{ formatInteger(totalCount) }}</span>
                    </div>

                    <!-- error :( -->
                    <div v-if="error">
                        <v-alert type="error">$t('error')</v-alert>
                    </div>
                    <!-- export in progress -->
                    <div v-else-if="waiting" class="pt-4">
                        <div class="py-2">{{ $t('export_running') }}</div>
                        <v-progress-linear
                                :value="progress"
                                height="30"
                        >
                            <span v-if="currentCount === null"><span class="fa fa-spin fa-spinner"></span> {{ $t('preparing') }}</span>
                            <span v-else>{{ formatInteger(currentCount) }} ({{ formatInteger(progress) }} %)</span>
                        </v-progress-linear>
                    </div>
                    <!-- data ready - show download button -->
                    <div v-else-if="resultUrl" class="pt-4">
                        <span>{{ $t('data_ready') }}</span>
                        <div class="d-flex pt-4">
                            <v-spacer></v-spacer>
                            <v-btn :href="resultUrl" color="warning" target="_blank" outlined>
                                <v-icon left>fa-download</v-icon>
                                {{ $t('download_data') }}
                            </v-btn>
                            <v-btn @click="showDialog = false" color="secondary" class="ml-2">{{ $t('close') }}</v-btn>
                        </div>
                    </div>
                    <!-- buttons to start export -->
                    <div v-else class="d-flex pt-4">
                        <v-spacer></v-spacer>
                        <v-btn v-if="!loadingCount" @click="startExport()" color="primary">{{ $t('start_export') }}</v-btn>
                        <v-btn @click="showDialog = false" color="secondary" class="ml-2">{{ $t('cancel') }}</v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>
    </span>
</template>

<script>
  import {mapActions, mapGetters, mapState} from 'vuex'
  import { formatInteger } from '../libs/numbers'
  import axios from 'axios'

  export default {
    name: "RawDataExportWidget",

    props: {
      title: {},
      platform: {},
      reportType: {},
      retryInterval: {required: false, default: 1000, type: Number},
    },

    data () {
      return {
        showDialog: false,
        loadingCount: false,
        waiting: false,
        totalCount: null,
        progressUrl: null,
        resultUrl: null,
        currentCount: 0,
        error: false,
      }
    },

    computed: {
      ...mapState({
        organization: 'selectedOrganizationId',
      }),
      ...mapGetters({
        dateStart: 'dateRangeStartText',
        dateEnd: 'dateRangeEndText',
      }),
      startUrl () {
        let url = `/api/raw-data-export/?start=${this.dateStart}&end=${this.dateEnd}`
        if (this.organization) {
          url += `&organization=${this.organization}`
        }
        if (this.title) {
          url += `&target=${this.title}`
        }
        if (this.platform) {
          url += `&platform=${this.platform}`
        }
        if (this.reportType) {
          url += `&report_type=${this.reportType}`
        }
        return url
      },
      progress () {
        if (this.totalCount) {
          return 100 * this.currentCount / this.totalCount
        }
        return 0
      }

    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger,
      async getRecordCount () {
        this.loadingCount = true
        try {
          let response = await axios.get(this.startUrl)
          this.totalCount = response.data.total_count
        } catch (error) {
          this.showSnackbar({content: 'Error loading record count: '+error, color: 'error'})
        } finally {
          this.loadingCount = false
        }
      },
      async startExport () {
        this.waiting = true
        try {
          let response = await axios.post(this.startUrl)
          this.progressUrl = response.data.progress_url
          this.resultUrl = response.data.result_url
          this.checkProgress()
        } catch (error) {
          this.showSnackbar({content: 'Error starting export: '+error, color: 'error'})
        }
      },
      async checkProgress () {
        try {
          let response = await axios.get(this.progressUrl)
          this.currentCount = response.data.count
          if (this.currentCount === this.totalCount) {
            this.waiting = false
          } else if (this.currentCount === -1) {
            this.error = true
          }
          if (this.waiting) {
            setTimeout(this.checkProgress, this.retryInterval)
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading export progress: '+error, color: 'error'})
        }
      },
      cleanup () {
        this.loadingCount = false
        this.waiting = false
        this.totalCount = null
        this.progressUrl = null
        this.resultUrl = null
        this.currentCount = 0
        this.error = false
      }
    },

    watch: {
      showDialog (value) {
        if (value) {
          this.cleanup()
          this.getRecordCount()
        }
      }
    }

  }
</script>

<style scoped>

</style>
