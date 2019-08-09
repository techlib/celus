<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    add_custom_param: Add custom parameter

cs:
    add_custom_param: Přidat vlastní parametr
</i18n>

<template>
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
                                        :label="$t('labels.value')"
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
                    <v-btn-toggle multiple v-model="selectedReportTypes">
                        <v-btn v-for="report in reportTypes" :value="report.code" :key="report.code">
                            {{ report.code }}
                        </v-btn>
                    </v-btn-toggle>
                </v-flex>
            </v-layout>
        </v-flex>
    </v-layout>

</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'

  export default {
    name: 'SushiCredentialsEditDialog',
    props: {
      credentialsObject: {},
    },
    data () {
      return {
        reportTypes: null,
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
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      credentialsPropToData () {
        let credentials = this.credentialsObject
        let extraParams = []
        for (let [key, value] in Object.entries(credentials.extra_params)) {
          extraParams.push({key: key, value: value})
        }
        let selectedReportTypes = []
        for (let reportType of credentials.active_counter_reports) {
          selectedReportTypes.push(reportType.code)
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
        this.selectedReportTypes = selectedReportTypes

      },
      async loadReportTypes () {
        try {
          let result = await axios.get('/api/counter-report-type/')
          this.reportTypes = result.data.filter(item => item.counter_version === this.counterVersion)
        } catch (error) {
          this.showSnackbar({content: 'Error loading report types: ' + error})
        }
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
