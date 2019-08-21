<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    data_file: Data file to upload
    data_file_placeholder: Upload a file with tabular data in CSV format

cs:
    data_file: Datový soubor k nahrání
    data_file_placeholder: Nahrajte soubor s tabulkovými daty ve formátu CSV
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
            <h2 v-if="platform">{{ platform.name }}</h2>
        </v-row>
    </v-container>
    <v-form
            ref="form"
            v-model="valid"
    >
        <v-container fluid elevation-3 pa-5>
            <v-row>
                <v-col cols="12" md="6">
                    <v-select
                            v-model="selectedReportTypeId"
                            :items="reportTypes"
                            item-text="name"
                            item-value="pk"
                            required
                            :label="$t('labels.report_type')"
                    >
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
                    <v-btn @click="postData" :disabled="!valid">Send</v-btn>
                </v-col>
            </v-row>
        </v-container>
    </v-form>
    </div>
</template>

<script>
  import axios from 'axios'
  import { mapActions, mapState } from 'vuex'

  export default {
    name: 'CustomDataUploadPage',
    props: {
      platformId: {required: true},
    },
    data () {
      return {
        dataFile: null,
        valid: false,
        platform: null,
        reportTypes: [],
        selectedReportTypeId: null,
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
        formData.append('report_type', this.selectedReportTypeId)
        try {
          let response = await axios.post(
            '/api/manual-data-upload/',
            formData,
            {headers: {'Content-Type': 'multipart/form-data'}}
          )
          this.showSnackbar({content: 'Data successfully sent', color: 'success'})
        } catch (error) {
          this.showSnackbar({content: 'Error sending data: ' + error})
        }
      },
      async loadPlatform () {
        if (this.organizationId) {
          try {
            let response = await axios.get(`/api/organization/${this.organizationId}/detailed-platform/${this.platformId}/`)
            this.platform = response.data
          } catch(error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
      async loadReportTypes () {
        let url = `/api/organization/${this.organizationId}/platform/${this.platformId}/reports/`
        if (url) {
          try {
            const response = await axios.get(url)
            this.reportTypes = response.data
            if (this.reportTypes.length > 0) {
              this.selectedReportTypeId = this.reportTypes[0].pk
            }
          } catch (error) {
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      filledIn (v) {
        if (v === null)
          return 'File must be filled in'
        return true
      }
    },
    mounted () {
      this.loadReportTypes()
      this.loadPlatform()
    }
  }
</script>

<style scoped>

</style>
