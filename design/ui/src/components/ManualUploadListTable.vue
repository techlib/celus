<i18n src="../locales/common.yaml"></i18n>

<template>
<div>
    <v-data-table
            :items="mdus"
            :headers="headers"
    >
        <template #item.user.last_name="{item}">
            {{ item.user.last_name }}, {{ item.user.first_name }}
        </template>

        <template #item.created="{item}">
            <span v-html="isoDateTimeFormatSpans(item.created)"></span>
        </template>

        <template #item.actions="{item}">
            <v-tooltip bottom v-if="item.import_batch">
                <template v-slot:activator="{ on }">
                    <v-btn
                            icon
                            small
                            color="secondary"
                            @click.stop="selectedBatch = item.import_batch.pk; dialogType = 'data'; showBatchDialog = true"
                            v-on="on"
                    >
                        <v-icon small>fa-microscope</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('actions.show_raw_data') }}</span>
            </v-tooltip>
            <v-tooltip bottom v-if="item.import_batch">
                <template v-slot:activator="{ on }">
                    <v-btn
                            icon
                            small
                            color="secondary"
                            @click.stop="selectedBatch = item.import_batch.pk; dialogType = 'chart'; showBatchDialog = true"
                            v-on="on"
                    >
                        <v-icon small>fa-chart-bar</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('actions.show_chart') }}</span>
            </v-tooltip>
            <v-tooltip bottom v-if="item.can_edit">
                <template v-slot:activator="{ on }">
                    <v-btn
                            icon
                            small
                            color="error"
                            v-on="on"
                    >
                        <v-icon small>fa fa-trash-alt</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('actions.delete') }}</span>
            </v-tooltip>
        </template>

    </v-data-table>

        <v-dialog
                v-model="showBatchDialog"
        >
            <v-card>
                <v-card-text>
                    <v-container
                            v-if="dialogType === 'data'"
                            fluid
                            class="pb-0"
                    >
                        <v-row class="pb-0">
                            <v-col cols="12" class="pb-0">
                                <AccessLogList :import-batch="selectedBatch" />
                            </v-col>
                        </v-row>
                    </v-container>
                    <ImportBatchChart
                            v-else-if="dialogType === 'chart'"
                            :import-batch-id="selectedBatch" />
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn
                            @click="showBatchDialog = false"
                            class="mr-2 mb-2"
                    >
                        {{ $t('actions.close') }}
                    </v-btn>
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
  import {isoDateTimeFormat, isoDateTimeFormatSpans} from '../libs/dates'

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
            text: 'uploaded',
            value: 'created',
          },
          {
            text: 'platform',
            value: 'platform.name',
          },
          {
            text: 'user',
            value: 'user.last_name',
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
      isoDateTimeFormat: isoDateTimeFormat,
      isoDateTimeFormatSpans: isoDateTimeFormatSpans,
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

<style lang="scss">

    span.time {
        font-weight: 300;
        font-size: 87.5%;
    }

</style>
