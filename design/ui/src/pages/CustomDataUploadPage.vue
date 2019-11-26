<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    data_file: Data file to upload
    data_file_placeholder: Upload a file with tabular data in CSV format
    error: Error
    dismiss: Dismiss
    step1: Data upload
    step2: Check before data import
    step3: Imported data view
    input_rows: Read input data rows
    output_logs: Generated logs
    imported_months: Data found for months
    overview: Overview
    upload: Upload
    add_report_type: Add new report type
    tab_chart: Chart
    tab_data: Data
    import: Import
    thats_all: That is all. The data were imported.
    return_to_platform: Go to platform page
    following_error_found: The following error was found when checking the imported data
    back_to_start: Back to data upload
    no_report_types: There are not reports defined for this platform - contact administrators to add some

cs:
    data_file: Datový soubor k nahrání
    data_file_placeholder: Nahrajte soubor s tabulkovými daty ve formátu CSV
    error: Chyba
    dismiss: Zavřít
    step1: Nahrání dat
    step2: Kontrola před importem
    step3: Zobrazení importovaných dat
    input_rows: Načtené datové řádky
    output_logs: Vygenerované záznamy
    imported_months: Data nalezena pro měsíce
    overview: Přehled
    upload: Nahrát
    add_report_type: Vytvořit nový typ reportu
    tab_chart: Graf
    tab_data: Data
    import: Importovat
    thats_all: To je vše. Data byla úspěšně importována.
    return_to_platform: Přejít na stránku platformy
    following_error_found: Při kontrole dat byla nalezena následující chyba
    back_to_start: Zpět na nahrání dat
    no_report_types: Pro tuto platformu nejsou definovány žádné reporty - kontaktujte administrátory pro jejich přidání
</i18n>

<template>
    <div>
        <v-container fluid>
            <v-row>
                <v-breadcrumbs :items="breadcrumbs" class="pl-0">
                    <template v-slot:item="props">
                        <router-link
                                v-if="props.item.linkName"
                                :to="{name: props.item.linkName, params: props.item.linkParams}"
                        >
                            {{ props.item.text }}
                        </router-link>
                        <span v-else>
                        {{ props.item.text }}
                    </span>
                    </template>
                </v-breadcrumbs>
            </v-row>
            <v-row>
                <v-col>
                    <h2 v-if="platform">{{ platform.name }}</h2>
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <CustomUploadInfoWidget />
                </v-col>
            </v-row>
        </v-container>
        <v-stepper v-model="step" vertical>
            <v-stepper-step step="1" :complete="step > 1">
                {{ $t('step1') }}
            </v-stepper-step>
            <v-stepper-content step="1">
                <v-form
                        ref="form"
                        v-model="valid"
                >
                    <v-container fluid elevation-3 pa-5>
                        <v-row no-gutters>
                            <v-col cols="12">
                                <ReportTypeInfoWidget
                                        v-if="selectedReportType"
                                        :report-type="selectedReportType"
                                />
                                <v-alert type="warning" v-else-if="reportTypesFetched">
                                    {{ $t('no_report_types') }}
                                </v-alert>
                            </v-col>
                        </v-row>
                        <v-row>
                            <v-col cols="12" md="6">
                                <v-select
                                        v-model="selectedReportType"
                                        :items="reportTypes"
                                        item-text="name"
                                        item-value="pk"
                                        required
                                        return-object
                                        :label="$t('labels.report_type')"
                                        :no-data-text="$t('no_report_types')"
                                        :rules="[filledIn]"
                                >
                                    <template v-slot:item="props">
                                        <span v-if="props.item.public">{{ props.item.name }}</span>
                                        <i v-else>{{ props.item.name }} <span class="font-weight-light">(private)</span></i>
                                    </template>
                                </v-select>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-file-input
                                        v-model="dataFile"
                                        prepend-icon="fa-table"
                                        show-size
                                        :label="$t('data_file')"
                                        :placeholder="$t('data_file_placeholder')"
                                        required
                                        :rules="[filledIn]"
                                >
                                </v-file-input>
                            </v-col>
                        </v-row>
                        <v-row>
                            <v-col>
                                <v-btn @click="postData" :disabled="!valid">{{ $t('upload' )}}</v-btn>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-form>
            </v-stepper-content>

            <v-stepper-step step="2" :complete="step > 2">
                {{ $t('step2') }}
            </v-stepper-step>
            <v-stepper-content step="2">
                <v-card>
                    <v-card-title>{{ $t('overview') }}</v-card-title>
                    <v-card-text>
                        <table v-if="preflightData">
                            <tr>
                                <th class="text-left">{{ $t('output_logs') }}</th>
                                <td class="text-right">{{ preflightData.log_count }}</td>
                            </tr>
                            <tr>
                                <th class="text-left">{{ $t('imported_months') }}</th>
                                <td>
                                    <ul class="no-decoration">
                                        <li v-for="month in preflightData.months" :key="month">{{ month.substring(0, 7) }}</li>
                                    </ul>
                                </td>
                            </tr>
                        </table>
                        <v-alert v-else-if="preflightError" type="error">
                            <strong v-text="$t('following_error_found')"></strong>:
                            <span v-text="preflightError"></span>
                        </v-alert>
                        <LargeSpinner v-else />
                    </v-card-text>
                    <v-card-actions>
                        <v-btn v-if="preflightData && !preflightError" @click="processUploadObject()" color="primary" :loading="uploadObjectProcessing">{{ $t('import') }}</v-btn>
                        <v-btn @click="backToStart()" v-text="$t('back_to_start')" color="secondary"></v-btn>
                    </v-card-actions>
                </v-card>

            </v-stepper-content>

            <v-stepper-step step="3" :complete="step > 3">
                {{ $t('step3') }}
            </v-stepper-step>
            <v-stepper-content step="3">
                <v-card>
                    <v-card-text v-if="importBatch">
                        <v-tabs v-model="tab" dark background-color="primary" fixed-tabs>
                            <v-tab href="#chart">{{ $t('tab_chart') }}</v-tab>
                            <v-tab href="#data">{{ $t('tab_data') }}</v-tab>
                        </v-tabs>
                        <v-tabs-items v-model="tab">
                            <v-tab-item value="chart">
                                <ImportBatchChart :import-batch-id="importBatch.pk" />
                            </v-tab-item>
                            <v-tab-item value="data">
                                <AccessLogList :import-batch="importBatch.pk" />
                            </v-tab-item>
                        </v-tabs-items>
                        <v-container>
                            <v-row>
                                <v-col cols="auto">
                                    {{ $t('thats_all') }}
                                </v-col>
                                <v-spacer></v-spacer>
                                <v-col cols="auto">
                                    <v-btn
                                            :to="{name: 'platform-detail', params: {platformId: platformId}}"
                                            color="secondary"
                                            >
                                        {{ $t('return_to_platform') }}
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </v-container>
                    </v-card-text>
                    <v-card-text v-else>
                        <LargeSpinner />
                    </v-card-text>
                </v-card>
            </v-stepper-content>

        </v-stepper>
        <v-dialog
                v-model="showErrorDialog"
                max-width="640px"
        >
            <v-card class="pa-3">
                <v-card-title>{{ $t('error') }}</v-card-title>
                <v-card-text>
                    <v-list>
                        <v-list-item v-for="(error, index) in errors" :key="index">
                            <v-list-item-avatar>
                                <v-icon color="error">fa-exclamation-circle</v-icon>
                            </v-list-item-avatar>
                            <v-list-item-content>{{ error }}</v-list-item-content>
                        </v-list-item>
                    </v-list>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn @click="showErrorDialog = false">{{ $t('dismiss') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
                <v-dialog
                v-model="showAddReportTypeDialog"
                max-width="880px"
        >
            <v-card class="pa-3">
                <v-card-title>{{ $t('add_report_type') }}</v-card-title>
                <v-card-text>
                    <ReportTypeCreateWidget>
                        <template v-slot:extra="props">
                            <v-btn @click="showAddReportTypeDialog = false">{{ $t('dismiss') }}</v-btn>
                        </template>
                    </ReportTypeCreateWidget>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<script>
  import axios from 'axios'
  import { mapActions, mapState } from 'vuex'
  import ImportBatchChart from '../components/ImportBatchChart'
  import AccessLogList from '../components/AccessLogList'
  import ReportTypeCreateWidget from '../components/ReportTypeCreateWidget'
  import LargeSpinner from '../components/LargeSpinner'
  import CustomUploadInfoWidget from '../components/CustomUploadInfoWidget'
  import ReportTypeInfoWidget from '../components/ReportTypeInfoWidget'

  export default {
    name: 'CustomDataUploadPage',
    components: {
      LargeSpinner,
      ReportTypeCreateWidget,
      ImportBatchChart,
      AccessLogList,
      CustomUploadInfoWidget,
      ReportTypeInfoWidget,
    },
    props: {
      platformId: {required: true},
      uploadObjectId: {required: false},
    },
    data () {
      return {
        dataFile: null,
        valid: false,
        platform: null,
        reportTypes: [],
        selectedReportType: null,
        showErrorDialog: false,
        errors: [],
        step: 1,
        uploadObject: null,
        preflightData: null,
        preflightError: null,
        importStats: null,
        importBatch: null,
        showAddReportTypeDialog: false,
        tab: 'chart',
        uploadObjectProcessing: false,
        reportTypesFetched: false,
      }
    },
    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      }),
      breadcrumbs () {
          return [
            {
              text: this.$t('pages.platforms'),
              linkName: 'platform-list',
            },
            {
              text: this.platform === null ? '' : this.platform.name,
              linkName: 'platform-detail',
              linkParams: {
                platformId: this.platformId
              }
            },
            {
              text: this.$t('actions.upload_custom_data'),
            },
        ]
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async postData () {
        let formData = new FormData();
        formData.append('data_file', this.dataFile)
        formData.append('organization', this.organizationId)
        formData.append('platform', this.platformId)
        formData.append('report_type', this.selectedReportType.pk)
        try {
          let response = await axios.post(
            '/api/manual-data-upload/',
            formData,
            {headers: {'Content-Type': 'multipart/form-data'}}
          )
          // this.showSnackbar({content: 'Data successfully sent', color: 'success'})
          this.uploadObject = response.data
          this.step = 2
          await this.$router.push({
            name: 'platform-upload-data-step2',
            params: {
              uploadObjectId: this.uploadObject.pk,
              platformId: this.platformId,
            }
          })
        } catch (error) {
          if (error.response && error.response.status === 400) {
            let info = error.response.data
            if ('data_file' in info) {
              // this.showSnackbar({content: 'Data file error: ' + info.data_file[0], color: 'error'})
              this.showErrorDialog = true
              this.errors = info.data_file
            }
          } else {
            this.showSnackbar({content: 'Error sending data: ' + error})
          }
        }
      },
      async loadPlatform () {
        if (this.organizationId) {
          try {
            let response = await axios.get(`/api/platform/${this.platformId}/`)
            this.platform = response.data
          } catch(error) {
              this.showSnackbar({content: 'Error loading platform details: '+error})
          }
        }
      },
      async loadReportTypes () {
        let url = `/api/platform/${this.platformId}/report-types/`
        if (url) {
          try {
            const response = await axios.get(url)
            this.reportTypes = response.data
            if (this.reportTypes.length > 0) {
              this.selectedReportType = this.reportTypes[0]
            }
            this.reportTypesFetched = true
          } catch (error) {
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      async loadPreflightData () {
        if (this.uploadObject) {
          let url = `/api/manual-data-upload/${this.uploadObject.pk}/preflight/`
          try {
            const response = await axios.get(url)
            this.preflightData = response.data
            this.preflightError = null
          } catch (error) {
            if (error.response && error.response.status === 400 && 'error' in error.response.data) {
              this.preflightError = error.response.data.error
            } else {
              this.showSnackbar({content: 'Error loading preflight data: ' + error})
            }
          }
        }
      },
      async processUploadObject () {
        this.uploadObjectProcessing = true
        if (this.uploadObject) {
          let url = `/api/manual-data-upload/${this.uploadObject.pk}/process/`
          try {
            const response = await axios.post(url, {})
            this.importStats = response.data.stats
            this.importBatch = response.data.import_batch
            this.step = 3
          } catch (error) {
            this.showSnackbar({content: 'Error processing data: ' + error})
          } finally {
            this.uploadObjectProcessing = false
          }
        }
      },
      async loadUploadObject () {
        if (this.uploadObjectId) {
          try {
            let response = await axios.get(`/api/manual-data-upload/${this.uploadObjectId}/`)
            this.uploadObject = response.data
            if (this.uploadObject.import_batch) {
              this.importBatch = this.uploadObject.import_batch
              this.step = 3
            } else {
              this.step = 2
              this.loadPreflightData()
            }
          } catch (error) {
            this.showSnackbar({content: 'Error loading upload data: ' + error})
          }
        }
      },
      filledIn (v) {
        if (v === null)
          return 'File must be filled in'
        return true
      },
      async backToStart () {
        this.uploadObject = null
        await this.$router.replace({
            name: 'platform-upload-data',
            params: {
              platformId: this.platformId,
            }
          })
      }
    },
    mounted () {
      this.loadReportTypes()
      this.loadPlatform()
      if (this.uploadObjectId) {
        this.loadUploadObject()
      }
    },
    watch: {
      showAddReportTypeDialog () {
        this.loadReportTypes()
      }
    }
  }
</script>

<style scoped lang="scss">

    ul.no-decoration {
        list-style: none;
    }

</style>
