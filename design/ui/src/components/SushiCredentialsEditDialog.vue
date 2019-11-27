<i18n src="../locales/common.yaml"></i18n>
<i18n src="../locales/dialog.yaml"></i18n>
<i18n>
en:
    add_custom_param: Add custom parameter
    test_dialog: Test SUSHI credentials
    all_versions_used: All versions already defined for this organization and platform - to make changes, edit the corresponding record
    save_and_test: Save and start test
    enabled: Enabled
    enabled_tooltip: Data for enabled credentials get automatically downloaded. To prevent downloads, disable the credentials.
    outside: Purchased outside of consortium
    outside_tooltip: Marks if access to this resource was purchased outside the consortium.
    only_managers_can_change: Only managers may change this option.
    title:
        edit_sushi_credentials: Edit SUSHI credentials
    delete_success: Sushi credentials were successfully removed

cs:
    add_custom_param: Přidat vlastní parametr
    test_dialog: Test přihlašovacích údajů SUSHI
    all_versions_used: Pro tuto platformu a organizaci jsou již všechny verze použity - pro změnu editujte příslušný záznam
    save_and_test: Uložit a spustit test
    enabled: Aktivní
    enabled_tooltip: Pro aktivní přístupové údaje se budou pravidelně stahovat data. Vypnutím toto stahování zrušíte.
    outside: Nákup mimo konzorcium
    outside_tooltip: Označuje přístupové údaje k nákupům mimo konzorcium.
    only_managers_can_change: Jen správci mohou měnit tuto hodnotu.
    title:
        edit_sushi_credentials: Přihlašovací údaje SUSHI
    delete_success: Přihlašovací údaje byly úspěšně odstraněny
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
                                    v-if="credentials"
                                    v-model="organization"
                                    :label="$t('organization')"
                                    disabled
                            >
                            </v-text-field>
                            <v-select v-else
                                      v-model="organization"
                                      :items="organizations"
                                      item-text="name"
                                      :label="$t('organization')"
                                      return-object
                                      :disabled="organizationSelected"
                            >
                            </v-select>
                        </v-flex>
                        <v-flex xs12 md6 px-5>
                            <v-text-field
                                    v-if="credentials"
                                    v-model="platform"
                                    :label="$t('platform')"
                                    disabled
                            >
                            </v-text-field>
                            <v-select v-else
                                      v-model="platform"
                                      :items="allowedPlatforms"
                                      item-text="short_name"
                                      :label="$t('platform')"
                                      return-object
                            >
                            </v-select>
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
                                    :items="allowedCounterVersions"
                                    :disabled="!!credentials"
                                    :no-data-text="$t('all_versions_used')"
                            >
                            </v-select>
                        </v-flex>
                        <v-flex xs12 sm10 px-5>
                            <v-text-field
                                    v-model="url"
                                    :label="$t('labels.url')"
                                    :error-messages="errors.url"
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
                <v-flex px-5 pt-6>
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
            <v-container fluid mx-2>
                <v-row no-gutters>
                    <v-col cols="auto">
                        <v-tooltip bottom>
                            <template v-slot:activator="{ on }">
                                <span v-on="on">
                                    <v-switch
                                            v-model="enabled"
                                            :label="$t('enabled')"
                                            class="pl-2 my-0"
                                    ></v-switch>
                                </span>
                            </template>
                            <span>{{ $t('enabled_tooltip') }}</span>
                        </v-tooltip>
                    </v-col>
                    <v-col cols="auto" class="ml-6">
                        <v-tooltip bottom>
                            <template v-slot:activator="{ on }">
                                <span v-on="on">
                                    <v-switch
                                            v-model="outsideConsortium"
                                            :label="$t('outside')"
                                            class="pl-2 my-0"
                                            :disabled="!userIsManager"
                                    ></v-switch>
                                </span>
                            </template>
                            <span>
                                {{ $t('outside_tooltip') }}
                                {{ userIsManager ? '' : $t('only_managers_can_change') }}
                            </span>
                        </v-tooltip>
                    </v-col>
                    <v-spacer></v-spacer>
                    <v-col cols="auto">
                        <v-btn color="error" @click="deleteObject()" class="mr-8">
                            <v-icon small class="mr-1">fa fa-trash-alt</v-icon>
                            {{ $t('delete') }}
                        </v-btn>
                        <v-btn color="secondary" @click="closeDialog()">
                            <v-icon small class="mr-1">fa fa-times</v-icon>
                            {{ $t('close') }}
                        </v-btn>
                        <v-btn color="warning" @click="saveAndTest()" :disabled="!valid">
                            <v-icon small class="mr-1">fa fa-play</v-icon>
                            {{ $t('save_and_test') }}
                        </v-btn>
                        <v-btn color="primary" @click="saveAndClose()" :disabled="!valid">
                            <v-icon small class="mr-1">fa fa-save</v-icon>
                            {{ $t('save') }}
                        </v-btn>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-actions>

        <v-dialog
                v-model="showTestDialog"
                max-width="800px"
        >
            <v-card>
                <v-card-title>{{ $t('test_dialog') }}</v-card-title>
                <v-card-text>
                    <SushiCredentialsTestWidget
                            :credentials="credentials"
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
  import { mapActions, mapGetters } from 'vuex'
  import SushiCredentialsTestWidget from './SushiCredentialsTestWidget'

  export default {
    name: 'SushiCredentialsEditDialog',
    components: {
      SushiCredentialsTestWidget,
    },
    props: {
      credentialsObject: {},
      value: {default: false},
      existingCredentials: {required: false, type: Array}
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
        organizations: [],
        platforms: [],
        errors: {},
        savedCredentials: null,
        enabled: false,
        outsideConsortium: true,
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
        organizationSelected: 'organizationSelected',
        userIsManager: 'showManagementStuff',
      }),
      credentials () {
        if (this.credentialsObject != null) {
          return this.credentialsObject
        }
        if (this.savedCredentials != null) {
          return this.savedCredentials
        }
        return null
      },
      apiData () {
        let extraParams = {}
        for (let rec of this.extraParams) {
          if (rec.key.trim())
            extraParams[rec.key] = rec.value
        }
        let data = {
          customer_id: this.customerId,
          requestor_id: this.requestorId,
          api_key: this.apiKey,
          url: this.url,
          counter_version: this.counterVersion,
          http_username: this.httpUsername,
          http_password: this.httpPassword,
          extra_params: extraParams,
          active_counter_reports: this.selectedReportTypes,
          enabled: this.enabled,
          outside_consortium: this.outsideConsortium,
        }
        if (this.credentials) {
          data['id'] = this.credentialsId
        } else {
          data['platform_id'] = this.platform.pk
          data['organization_id'] = this.organization.pk
        }
        return data
      },
      reportTypes () {
        return this.allReportTypes.filter(item => item.counter_version === this.counterVersion)
      },
      valid () {
        if (this.credentials) {
          return (this.selectedReportTypes.length > 0 && this.url && this.customerId)
        } else {
          return (this.selectedReportTypes.length > 0 && this.url && this.customerId &&
            this.platform !== null && this.counterVersion)
        }
      },
      allowedPlatforms () {
        return this.platforms
      },
      allowedCounterVersions () {
        let versions = [4, 5]
        if (!this.existingCredentials) {
          return versions
        }
        // we have a list of existing credentials - we will filter the possibilities according
        // to what is already defined
        let existing = []
        for (let cred of this.existingCredentials) {
          if (cred.organization.pk === this.organization.pk && cred.platform.pk === this.platform.pk) {
            existing.push(cred.counter_version)
          }
        }
        return versions.filter(item => existing.indexOf(item) < 0)
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      credentialsPropToData () {
        let credentials = this.credentials
        if (!credentials) {
          // no credentials - we init to the initial state
          this.organizationId = null
          this.organization = ''
          this.platformId = null
          this.platform = ''
          this.requestorId = ''
          this.customerId = ''
          this.counterVersion = null
          this.url = ''
          this.httpUsername = ''
          this.httpPassword = ''
          this.apiKey = ''
          this.extraParams = []
          this.selectedReportTypes = []
          this.credentialsId = null
          this.errors = {}
          this.savedCredentials = null
          this.enabled = false
          this.outsideConsortium = true
        } else {
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
          this.credentialsId = credentials.pk
          this.enabled = credentials.enabled
          this.outsideConsortium = credentials.outside_consortium
        }
      },
      async loadReportTypes () {
        try {
          let result = await axios.get('/api/counter-report-type/')
          this.allReportTypes = result.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading report types: ' + error})
        }
      },
      async loadOrganizations () {
        if (this.organizationSelected) {
          // we have a specific organization selected - we use it
          this.organizations = [this.selectedOrganization]
          this.organization = this.selectedOrganization
        } else {
          try {
            let result = await axios.get('/api/organization/')
            this.organizations = result.data
            this.organization = this.organizations[0]
          } catch (error) {
            this.showSnackbar({content: 'Error loading organizations: ' + error})
          }
        }
      },
      async loadPlatforms () {
        try {
          let result = await axios.get('/api/platform/')
          this.platforms = result.data
          this.platform = this.platforms[0]
        } catch (error) {
          this.showSnackbar({content: 'Error loading platforms: ' + error})
        }
      },
      closeDialog () {
        this.$emit('input', false)
      },
      async saveData () {
        this.errors = {}
        try {
          let response = null
          if (this.credentials) {
            // we have existing credentials - we patch it
            response = await axios.patch(
              `/api/sushi-credentials/${this.credentialsId}/`,
              this.apiData,
            )
          } else {
            // we create new credentials
            response = await axios.post(
              `/api/sushi-credentials/`,
              this.apiData,
            )
          }
          this.savedCredentials = response.data
          this.showSnackbar({content: 'Successfully saved SUSHI credentials', color: 'success'})
          this.$emit('update-credentials', response.data)
          return true
        } catch (error) {
          this.showSnackbar({content: 'Error saving SUSHI credentials: ' + error, color: 'error'})
          if (error.response != null) {
            this.processErrors(error.response.data)
          }
          return false
        }
      },
      async deleteObject () {
        if (this.credentials) {
          // we have existing credentials - we patch it
          try {
            await axios.delete(`/api/sushi-credentials/${this.credentialsId}/`)
            this.$emit('deleted', {id: this.credentialsId})
            this.$emit('input', false)
            this.showSnackbar({content: this.$t('delete_success'), color: 'success'})
          } catch (error) {
            this.showSnackbar({content: 'Error deleting SUSHI credentials: ' + error, color: 'error'})
          }
        }
      },
      processErrors (errors) {
        this.errors = errors
      },
      async saveAndClose () {
        let ok = await this.saveData()
        if (ok) {
          this.$emit('input', false)
        }
      },
      async saveAndTest () {
        let ok = await this.saveData()
        if (ok) {
          if (this.$refs.testWidget) {
            this.$refs.testWidget.clean()
          }
          this.showTestDialog = true
        }
      },
      stopTestDialog () {
        if (this.$refs.testWidget) {
          this.$refs.testWidget.clean()
        }
        this.showTestDialog = false
      },
      init () {
        this.savedCredentials = null
        this.credentialsPropToData()
        if (this.credentials == null) {
          this.loadOrganizations()
          this.loadPlatforms()
        }
      }
    },
    mounted () {
      this.loadReportTypes()
      this.init()
    },
    watch: {
      credentialsObject () {
        this.init()
      },
      value (value) {
        if (value === true)
          this.init()
      }
    }

  }
</script>

<style scoped>

</style>
