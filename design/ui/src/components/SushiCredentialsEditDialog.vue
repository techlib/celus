<i18n src="../locales/common.yaml"></i18n>
<i18n src="../locales/dialog.yaml"></i18n>
<i18n>
en:
    add_custom_param: Add custom parameter
    test_dialog: Test SUSHI credentials
    title:
        edit_sushi_credentials: Edit SUSHI credentials

cs:
    add_custom_param: Přidat vlastní parametr
    test_dialog: Test přihlašovacích údajů SUSHI
    title:
        edit_sushi_credentials: Přihlašovací údaje SUSHI
</i18n>



<template>
    <v-card>
        <v-card-title class="headline">{{ $t('title.edit_sushi_credentials') }}</v-card-title>
        <v-card-text>
            <v-layout row pa-4>
                <v-flex xs12 px-4>
                    <v-layout row>
                        <v-flex xs12 md6 px-5>
                            <v-text-field
                                    v-model="organization"
                                    :label="$t('organization')"
                                    disabled
                            >
                            </v-text-field>
                        </v-flex>
                        <v-flex xs12 md6 px-5>
                            <v-text-field
                                    v-model="platform"
                                    :label="$t('platform')"
                                    disabled
                            >
                            </v-text-field>
                        </v-flex>
                    </v-layout>
                </v-flex>
                <v-flex xs12 pt-5 px-4>
                    <v-layout row>
                        <v-flex xs12 sm6 px-5>
                            <v-text-field
                                    v-model="requestorId"
                                    :label="$t('labels.requestor_id')"
                            >
                            </v-text-field>
                        </v-flex>
                        <v-flex xs12 sm6 px-5>
                            <v-text-field
                                    v-model="customerId"
                                    :label="$t('labels.customer_id')"
                            >
                            </v-text-field>
                        </v-flex>
                    </v-layout>
                </v-flex>
                <v-flex xs12 pt-3 px-4>
                    <v-layout row>
                        <v-flex xs6 sm2 px-5>
                            <v-select
                                    v-model="counterVersion"
                                    :label="$t('labels.counter_version')"
                                    :items="[4, 5]"
                                    disabled
                            >
                            </v-select>
                        </v-flex>
                        <v-flex xs12 sm10 px-5>
                            <v-text-field
                                    v-model="url"
                                    :label="$t('labels.url')"
                            >
                            </v-text-field>
                        </v-flex>
                    </v-layout>
                </v-flex>
                <v-flex xs12>
                    <v-expansion-panels class="px-2 pt-4">
                        <v-expansion-panel>
                            <v-expansion-panel-header>{{ $t('labels.http_authentication') }}</v-expansion-panel-header>
                            <v-expansion-panel-content>
                                <v-layout row>
                                    <v-flex xs12 sm6 px-5>
                                        <v-text-field
                                                v-model="httpUsername"
                                                :label="$t('labels.http_username')"
                                        >
                                        </v-text-field>
                                    </v-flex>
                                    <v-flex xs12 sm6 px-5>
                                        <v-text-field
                                                v-model="httpPassword"
                                                :label="$t('labels.http_password')"
                                        >
                                        </v-text-field>
                                    </v-flex>
                                </v-layout>
                            </v-expansion-panel-content>
                        </v-expansion-panel>
                        <v-expansion-panel>
                            <v-expansion-panel-header>{{ $t('labels.extra_params') }}</v-expansion-panel-header>
                            <v-expansion-panel-content>
                                <v-layout row>
                                    <v-flex xs12 px-5>
                                        <v-text-field
                                                v-model="apiKey"
                                                :label="$t('labels.api_key')"
                                        >
                                        </v-text-field>
                                    </v-flex>
                                </v-layout>
                                <v-layout row v-for="(param, index) in extraParams" :key="index">
                                    <v-flex xs12 sm6 px-5>
                                        <v-text-field
                                                v-model="param.key"
                                                :label="$t('labels.variable')"
                                        >
                                        </v-text-field>
                                    </v-flex>
                                    <v-flex xs12 sm6 px-5>
                                        <v-text-field
                                                v-model="param.value"
                                                :label="$t('labels.variable_value')"
                                        >
                                        </v-text-field>
                                    </v-flex>
                                </v-layout>
                                <v-layout>
                                    <v-flex xs12 px-2 pt-2>
                                        <v-btn @click="extraParams.push({})" outlined color="green">
                                            <v-icon left x-small>fa-plus</v-icon>
                                            {{ $t('add_custom_param') }}
                                        </v-btn>
                                    </v-flex>
                                </v-layout>
                            </v-expansion-panel-content>
                        </v-expansion-panel>
                    </v-expansion-panels>
                </v-flex>
                <v-flex pa-5 pt-6>
                    <v-layout row>
                        <v-flex xs12>
                            <h4>Active report types</h4>
                        </v-flex>
                        <v-flex xs12 pt-2>
                            <v-btn-toggle multiple v-model="selectedReportTypes" >
                                <v-btn v-for="report in reportTypes" :value="report.id" :key="report.id" outlined color="primary">
                                    {{ report.code }}
                                </v-btn>
                            </v-btn-toggle>
                        </v-flex>
                    </v-layout>
                </v-flex>
            </v-layout>

        </v-card-text>
        <v-card-actions>
            <v-layout pb-3 pr-5 justify-end>
                <v-btn color="warning" @click="startTestDialog()">{{ $t('test') }}</v-btn>
                <v-btn color="secondary" @click="closeDialog()">{{ $t('close') }}</v-btn>
                <v-btn color="primary" @click="saveAndClose()" :disabled="!valid">{{ $t('save') }}</v-btn>
            </v-layout>
        </v-card-actions>

        <v-dialog
                v-model="showTestDialog"
        >
            <v-card>
                <v-card-title>{{ $t('test_dialog') }}</v-card-title>
                <v-card-text>
                    <SushiCredentialsTestWidget
                            :credentials="credentialsObject"
                            :report-types="selectedReportTypes"
                            ref="testWidget"

                    >

                    </SushiCredentialsTestWidget>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="secondary" @click="stopTestDialog()">{{ $t('close') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-card>

</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'
  import SushiCredentialsTestWidget from './SushiCredentialsTestWidget'

  export default {
    name: 'SushiCredentialsEditDialog',
    components: {
      SushiCredentialsTestWidget,
    },
    props: {
      credentialsObject: {},
      value: {default: false},
    },
    data () {
      return {
        allReportTypes: [],
        organizationId: null,
        organization: '',
        platformId: null,
        platform: '',
        requestorId: '',
        customerId: '',
        counterVersion: null,
        url: '',
        httpUsername: '',
        httpPassword: '',
        apiKey: '',
        extraParams: [],
        selectedReportTypes: [],
        credentialsId: null,
        showTestDialog: false,
      }
    },
    computed: {
      apiData () {
        let extraParams = {}
        for (let rec of this.extraParams) {
          if (rec.key.trim())
            extraParams[rec.key] = rec.value
        }
        return {
          id: this.credentialsId,
          customer_id: this.customerId,
          requestor_id: this.requestorId,
          api_key: this.api_key,
          url: this.url,
          counter_version: this.counterVersion,
          http_username: this.httpUsername,
          http_password: this.httpPassword,
          extra_params: extraParams,
          active_counter_reports: this.selectedReportTypes,
        }
      },
      reportTypes () {
        return this.allReportTypes.filter(item => item.counter_version === this.counterVersion)
      },
      valid () {
        return (this.selectedReportTypes.length > 0 && this.url && this.requestorId)
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      credentialsPropToData () {
        let credentials = this.credentialsObject
        if (!credentials) {
          return
        }
        let extraParams = []
        for (let [key, value] of Object.entries(credentials.extra_params)) {
          extraParams.push({key: key, value: value})
        }
        this.organizationId = credentials.organization.id
        this.organization = credentials.organization.name
        this.platformId = credentials.platform.id
        this.platform = credentials.platform.name
        this.requestorId = credentials.requestor_id
        this.customerId = credentials.customer_id
        this.counterVersion = credentials.counter_version
        this.url = credentials.url
        this.httpUsername = credentials.http_username
        this.httpPassword = credentials.http_password
        this.apiKey = credentials.api_key
        this.extraParams = extraParams
        this.selectedReportTypes = [...credentials.active_counter_reports]
        this.credentialsId = credentials.id

      },
      async loadReportTypes () {
        try {
          let result = await axios.get('/api/counter-report-type/')
          this.allReportTypes = result.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading report types: ' + error})
        }
      },
      closeDialog () {
        this.$emit('input', false)
      },
      async saveData () {
        try {
          let result = await axios.patch(
            `/api/sushi-credentials/${this.credentialsId}/`,
            this.apiData,
            )
          this.showSnackbar({content: 'Successfully saved SUSHI credentials', color: 'success'})
          this.$emit('updte-credentials', result.data)
          return true
        } catch (error) {
          this.showSnackbar({content: 'Error saving SUSHI credentials: ' + error, color: 'error'})
          return false
        }
      },
      async saveAndClose () {
        let ok = await this.saveData()
        if (ok) {
          this.$emit('input', false)
        }
      },
      startTestDialog () {
        if (this.$refs.testWidget) {
          this.$refs.testWidget.clean()
        }
        this.showTestDialog = true
      },
      stopTestDialog () {
        if (this.$refs.testWidget) {
          this.$refs.testWidget.clean()
        }
        this.showTestDialog = false
      }
    },
    mounted () {
      this.credentialsPropToData()
      this.loadReportTypes()
    },
    watch: {
      credentialsObject () {
        this.credentialsPropToData()
      }
    }

  }
</script>

<style scoped>

</style>
