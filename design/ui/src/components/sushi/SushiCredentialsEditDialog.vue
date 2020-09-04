<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
    add_custom_param: Add custom parameter
    add_custom_param_tooltip: Use this to add parameters for which there is no specific field elsewhere.
    test_dialog: Test SUSHI credentials
    all_versions_used: All versions already defined for this organization and platform - to make changes, edit the corresponding record
    save_and_test: Save & test harvesting
    save_and_test_tooltip: Saves current version of credentials and displays a dialog allowing harvesting of data for specified period using these credentials. Very useful to <strong>validate credentials and/or manually download data</strong>.
    outside: Purchased outside of consortium
    outside_tooltip: Marks if access to this resource was purchased outside the consortium.
    only_managers_can_change: Only managers may change this option.
    title:
        edit_sushi_credentials: Edit SUSHI credentials
    delete_success: Sushi credentials were successfully removed
    title_label: Title
    title_tooltip: You can give the credentials a descriptive title for easier identification. A title is required when you have more than one set of credentials for the same SUSHI server.
    credentials_conflict: "|{n} record for same platform/version|{n} records for same platform/version"
    title_in_conflict: <strong>Use a different title</strong>. When creating more than one set of credentials for the same organization, platform and COUNTER version, you need to use distinct titles in order to distinguish between the sets.
    optional_args: Extra attributes - fill only if instructed by provider
    optional_args_tooltip: The following section is used for attributes which are only used by some providers. If the credentials given to you by the provider contain fields that do not correspond to any of the fields above, you can fill them in here.

cs:
    add_custom_param: Přidat vlastní parametr
    add_custom_param_tooltip: Použijte toto tlačítko pro data, pro která nenajdete odpovídající políčko jinde.
    test_dialog: Test přihlašovacích údajů SUSHI
    all_versions_used: Pro tuto platformu a organizaci jsou již všechny verze použity - pro změnu editujte příslušný záznam
    save_and_test: Uložit a otestovat stahování
    outside: Nákup mimo konzorcium
    outside_tooltip: Označuje přístupové údaje k nákupům mimo konzorcium.
    only_managers_can_change: Jen správci mohou měnit tuto hodnotu.
    title:
        edit_sushi_credentials: Přihlašovací údaje SUSHI
    delete_success: Přihlašovací údaje byly úspěšně odstraněny
    title_label: Název
    title_tooltip: Přihlašovacím údajům můžete přiřadit název pro lepší identifikaci. Název je také vyžadován v případě, že máte více než jednu sadu přihlašovacích údajů pro stejný SUSHI server.
    credentials_conflict: "|{n} záznam pro stejnou platformu/verzi|{n} záznamy pro stejnou platformu/verzi|{n} záznamů pro stejnou platformu/verzi"
    title_in_conflict: <strong>Použijte jiný název</strong>. Pokud vytváříte více přihlašovacích údajů pro stejnout organizaci, platformu a verzi COUNTER, musíte použít různé názvy, aby bylo možné přihlašovací údaje rozlišit.
    optional_args: Další parametry - vyplňte pouze pokud to poskytovatel vyžaduje
    optional_args_tooltip: Následující sekce je určena pro parametry, které jsou používány pouze některými poskytovateli. Pokud přihlašovací údaje, které jste obdrželi od poskytovatele obsahují údaje, pro které není ve formuláři výše položka, můžete je vyplnit zde.
</i18n>



<template>
    <v-card>
        <v-card-title class="headline">{{ $t('title.edit_sushi_credentials') }}</v-card-title>
        <v-card-text>
            <v-container fluid>
                <v-row>
                    <v-col cols="12" :md="4">
                        <v-tooltip bottom max-width="600px">
                            <template #activator="{ on }">
                                <v-text-field
                                        v-model="title"
                                        :label="$t('title_label')"
                                        v-on="on"
                                >
                                    <template v-slot:append v-if="titleHint">
                                        <v-tooltip bottom v-if="titleHint">
                                            <template #activator="{on}">
                                                <v-icon v-on="on" small color="warning">fa-exclamation-triangle</v-icon>
                                            </template>
                                            <div v-html="titleHint" style="max-width: 400px"></div>
                                        </v-tooltip>

                                    </template>
                                </v-text-field>
                            </template>
                            {{ $t('title_tooltip') }}
                        </v-tooltip>
                    </v-col>
                    <v-col cols="12" :md="4">
                        <v-text-field
                                v-if="credentials"
                                :value="organization.name"
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
                    </v-col>
                    <v-col cols="12" :md="4">
                        <v-text-field
                                v-if="credentials || fixedPlatform"
                                :value="activePlatform.name"
                                :label="$t('platform')"
                                disabled
                        >
                        </v-text-field>
                        <v-select v-else
                                  v-model="platform"
                                  :items="allowedPlatforms"
                                  item-text="name"
                                  :label="$t('platform')"
                                  return-object
                                  :loading="loadingPlatforms"
                        >
                        </v-select>
                    </v-col>
                </v-row>

                <v-row>
                    <v-col cols="12" :sm="6">
                        <v-text-field
                                v-model="requestorId"
                                :label="$t('labels.requestor_id')"
                        >
                        </v-text-field>
                    </v-col>
                    <v-col cols="12" :sm="6">
                        <v-text-field
                                v-model="customerId"
                                :label="$t('labels.customer_id')"
                        >
                        </v-text-field>
                    </v-col>
                </v-row>

                <v-row>
                    <v-col cols="6" :sm="3">
                        <v-select
                                v-model="counterVersion"
                                :label="$t('labels.counter_version')"
                                :items="allowedCounterVersions"
                                :disabled="!!credentials"
                                :no-data-text="$t('all_versions_used')"
                                :hint="versionHint"
                        >
                        </v-select>
                    </v-col>
                    <v-col cols="12" :sm="9">
                        <v-text-field
                                v-model="url"
                                :label="$t('labels.url')"
                                :error-messages="errors.url"
                        >
                        </v-text-field>
                    </v-col>
                </v-row>


                <v-row>
                    <v-col class="pb-1" cols="auto">
                        <v-tooltip bottom max-width="600px">
                            <template #activator="{ on }">
                                <h4 v-on="on" class="font-weight-light pl-2" v-text="$t('optional_args')"></h4>
                            </template>
                            {{ $t('optional_args_tooltip') }}
                        </v-tooltip>
                    </v-col>
                </v-row>
                <v-row>
                    <v-col cols="12" class="pt-0">
                        <v-expansion-panels>
                            <v-expansion-panel>
                                <v-expansion-panel-header>{{ $t('labels.http_authentication') }}</v-expansion-panel-header>
                                <v-expansion-panel-content>
                                    <v-container>
                                        <v-row>
                                            <v-col cols="12" :sm="6">
                                                <v-text-field
                                                        v-model="httpUsername"
                                                        :label="$t('labels.http_username')"
                                                >
                                                </v-text-field>
                                            </v-col>
                                            <v-col cols="12" :sm="6">
                                                <v-text-field
                                                        v-model="httpPassword"
                                                        :label="$t('labels.http_password')"
                                                >
                                                </v-text-field>
                                            </v-col>
                                        </v-row>
                                    </v-container>
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
                                            <v-tooltip bottom>
                                                <template #activator="{ on }">
                                                    <v-btn v-on="on" @click="extraParams.push({})" outlined color="green">
                                                        <v-icon left x-small>fa-plus</v-icon>
                                                        {{ $t('add_custom_param') }}
                                                    </v-btn>
                                                </template>
                                                {{ $t('add_custom_param_tooltip') }}
                                            </v-tooltip>
                                        </v-flex>
                                    </v-layout>
                                </v-expansion-panel-content>
                            </v-expansion-panel>
                        </v-expansion-panels>
                    </v-col>
                </v-row>

                <v-divider />
                <v-row>
                    <v-col cols="12" class="pt-4 pb-0">
                        <h4>Active report types</h4>
                    </v-col>
                    <v-col cols="12">
                        <v-btn-toggle multiple v-model="selectedReportTypes" >
                            <v-tooltip v-for="report in reportTypes" bottom :key="report.id">
                                <template #activator="{ on }">
                                    <v-btn
                                            :value="report.id"
                                            outlined
                                            color="primary"
                                            v-on="on"
                                    >
                                        {{ report.code }}
                                    </v-btn>
                                </template>
                                {{ report.name || report.code}}
                            </v-tooltip>
                        </v-btn-toggle>
                    </v-col>
                </v-row>
            </v-container>
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
                                            :label="$t('sushi.enabled')"
                                            class="pl-2 my-0"
                                    ></v-switch>
                                </span>
                            </template>
                            <span>{{ $t('sushi.enabled_tooltip') }}</span>
                        </v-tooltip>
                    </v-col>
                    <v-col cols="auto" class="ml-6" v-if="consortialInstall">
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
                        <v-btn v-if="credentials" color="error" @click="deleteObject()" class="mr-8">
                            <v-icon small class="mr-1">fa fa-trash-alt</v-icon>
                            {{ $t('delete') }}
                        </v-btn>
                        <v-btn color="secondary" @click="closeDialog()" class="mr-2">
                            <v-icon small class="mr-1">fa fa-times</v-icon>
                            {{ $t('close') }}
                        </v-btn>
                        <v-tooltip bottom max-width="600px">
                            <template #activator="{ on }">
                                <v-btn color="warning" @click="saveAndTest()" :disabled="!valid" class="mr-2" v-on="on">
                                    <v-icon small class="mr-1">fa fa-play</v-icon>
                                    {{ $t('save_and_test') }}
                                </v-btn>
                            </template>
                            <span v-html="$t('save_and_test_tooltip')"></span>
                        </v-tooltip>
                        <v-btn color="primary" @click="saveAndClose()" :disabled="!valid" class="mr-2">
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
                            v-if="showTestDialog"
                            :credentials="[credentials]"
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
      existingCredentials: {required: false, type: Array},
      fixedPlatform: {required: false, type: Number},
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
        showTestDialog: false,
        organizations: [],
        platforms: [],
        errors: {},
        savedCredentials: null,
        enabled: false,
        outsideConsortium: true,
        title: '',
        loadingPlatforms: false,
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
        organizationSelected: 'organizationSelected',
        userIsManager: 'showManagementStuff',
        consortialInstall: 'consortialInstall',
      }),
      credentials () {
        if (this.credentialsObject) {
          return this.credentialsObject
        }
        if (this.savedCredentials) {
          return this.savedCredentials
        }
        return null
      },
      activePlatform () {
        if (this.credentials) {
          return this.credentials.platform
        } else if (this.fixedPlatform) {
          return this.fixedPlatform
        }
        return this.platform
      },
      apiData () {
        let extraParams = {}
        for (let rec of this.extraParams) {
          if (rec.key.trim())
            extraParams[rec.key] = rec.value
        }
        let data = {
          title: this.title,
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
          data['id'] = this.credentials.pk
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
        if (this.conflictingCredentials) {
          return false
        }
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
        return [4, 5]
      },
      versionHint () {
        if (!this.existingCredentials) {
          return null
        }
        if (this.similarCredentials > 0) {
          return this.$tc('credentials_conflict', this.similarCredentials.length)
        }
        return null
      },
      conflictingCredentials () {
        /*
        * return true if there are credentials with the same organization, platform and counter
        * version and also the same name - this is not allowed and should be reflected in the
        * UI
        * */
        return !!(this.similarCredentials.filter(cred => cred.title == this.title).length)
      },
      similarCredentials () {
        /*
        list of credentials that have the same organization, platform and counter version
         */
        if (this.existingCredentials) {
          return this.existingCredentials.filter(
            cred =>
              cred.organization.pk === this.organization.pk &&
              cred.platform.pk === this.platform.pk &&
              cred.counter_version === this.counterVersion
          )
        }
        return []
      },
      titleHint () {
        if (this.conflictingCredentials) {
          return this.$t('title_in_conflict')
        }
        return false
      },
      platformsBaseUrl () {
        if (this.organization && this.organization.pk) {
          return `/api/organization/${this.organization.pk}/all-platform/`
        }
        return null
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
          this.title = ''
          this.organizationId = null
          this.organization = {name: ''}
          this.platformId = null
          this.platform = {name: ''}
          this.requestorId = ''
          this.customerId = ''
          this.counterVersion = null
          this.url = ''
          this.httpUsername = ''
          this.httpPassword = ''
          this.apiKey = ''
          this.extraParams = []
          this.selectedReportTypes = []
          this.errors = {}
          this.savedCredentials = null
          this.enabled = false
          this.outsideConsortium = true
        } else {
          let extraParams = []
          for (let [key, value] of Object.entries(credentials.extra_params)) {
            extraParams.push({key: key, value: value})
          }
          this.title = credentials.title
          this.organizationId = credentials.organization.id
          this.organization = credentials.organization
          this.platformId = credentials.platform.id
          this.platform = credentials.platform
          this.requestorId = credentials.requestor_id
          this.customerId = credentials.customer_id
          this.counterVersion = credentials.counter_version
          this.url = credentials.url
          this.httpUsername = credentials.http_username
          this.httpPassword = credentials.http_password
          this.apiKey = credentials.api_key
          this.extraParams = extraParams
          this.selectedReportTypes = [...credentials.active_counter_reports]
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
        if (this.platformsBaseUrl) {
          this.platforms = []
          this.loadingPlatforms = true
          if (this.fixedPlatform) {
            try {
              let result = await axios.get(this.platformsBaseUrl + this.fixedPlatform + '/')
              this.platform = result.data
              this.platforms = [this.platform]
            } catch (error) {
              this.showSnackbar({content: `Error loading platform id:${this.fixedPlatform}: ` + error})
            } finally {
              this.loadingPlatforms = false
            }
          } else {
            try {
              let result = await axios.get(this.platformsBaseUrl)
              this.platforms = result.data
              this.platform = this.platforms[0]
            } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: ' + error})
            } finally {
              this.loadingPlatforms = false
            }
          }
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
              `/api/sushi-credentials/${this.credentials.pk}/`,
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
          try {
            await axios.delete(`/api/sushi-credentials/${this.credentials.pk}/`)
            this.$emit('deleted', {id: this.credentials.pk})
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
      },
      platformsBaseUrl () {
        this.loadPlatforms()
      }
    }

  }
</script>

<style scoped>

</style>
