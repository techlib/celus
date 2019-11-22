<template>
<div>
    <v-data-table
            :items="mdus"
            :headers="headers"
    >
        <template #item.actions="{item}">
            <v-btn v-if="item.can_edit" small color="error" icon>
                <v-icon small>fa fa-trash-alt</v-icon>
            </v-btn>


            <v-tooltip bottom v-if="item.import_batch">
                <template v-slot:activator="{ on }">
                    <v-btn text small color="secondary" @click.stop="selectedBatch = item.import_batch.pk; dialogType = 'data'; showBatchDialog = true" v-on="on">
                        <v-icon left small>fa-microscope</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('show_raw_data') }}</span>
            </v-tooltip>
            <v-tooltip bottom v-if="item.import_batch">
                <template v-slot:activator="{ on }">
                    <v-btn text small color="secondary" @click.stop="selectedBatch = item.import_batch.pk; dialogType = 'chart'; showBatchDialog = true" v-on="on">
                        <v-icon left small>fa-chart-bar</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('show_chart') }}</span>
            </v-tooltip>
        </template>

    </v-data-table>

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
</div>
</template>

<script>
  import {mapActions, mapState} from 'vuex'
  import axios from 'axios'
  import AccessLogList from './AccessLogList'
  import ImportBatchChart from './ImportBatchChart'

  export default {
    name: "ManualUploadListTable",

    components: {
      AccessLogList,
      ImportBatchChart
    },

    data () {
      return {
        mdus: [],
        loading: false,
        showBatchDialog: false,
        selectedBatch: null,
        dialogType: 'chart',
      }
    },

    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      headers () {
        return [
          {
            text: 'pk',
            value: 'pk',
          },
          {
            text: 'platform',
            value: 'platform',
          },
          {
            text: 'actions',
            value: 'actions',
          }
        ]
      },
      url () {
        if (this.selectedOrganizationId) {
          return `/api/organization/${this.selectedOrganizationId}/manual-data-upload/`
        }
        return null
      }

    },

    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async fetchMDUs () {
        if (this.url) {
          this.loading = true
          try {
            const response = await axios.get(this.url)
            this.mdus = response.data
          } catch (error) {
            this.showSnackbar({content: 'Error loading manual upload data', color: 'error'})
          } finally {
            this.loading = false
          }
        }
      }
    },

    watch: {
      url () {
        this.fetchMDUs()
      }
    },

    mounted () {
      this.fetchMDUs()
    }

  }
</script>

<style scoped>

</style>
