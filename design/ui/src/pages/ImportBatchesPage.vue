<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    show_raw_data: Show raw data
    show_chart: Show charts

cs:
    show_raw_data: Zobrazit data
    show_chart: Zobrazit grafy
</i18n>

<template>
    <div>
    <v-data-table
            :items="batches"
            :headers="headers"
            :loading="loading"
    >
        <!--template v-slot:item.created="props">
            <span>{{ props.item.created }}</span>
        </template-->
        <template v-slot:item.actions="props">
            <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                    <v-btn text small color="secondary" @click.stop="selectedBatch = props.item.pk; dialogType = 'data'; showDialog = true" v-on="on">
                        <v-icon left small>fa-microscope</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('show_raw_data') }}</span>
            </v-tooltip>
            <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                    <v-btn text small color="secondary" @click.stop="selectedBatch = props.item.pk; dialogType = 'chart'; showDialog = true" v-on="on">
                        <v-icon left small>fa-chart-bar</v-icon>
                    </v-btn>
                </template>
                <span>{{ $t('show_chart') }}</span>
            </v-tooltip>
        </template>
    </v-data-table>

    <v-dialog
            v-model="showDialog"
    >
        <v-card>
            <v-card-text>
                <AccessLogList v-if="dialogType === 'data'" :import-batch="this.selectedBatch" />
                <ImportBatchChart v-else-if="dialogType === 'chart'" :import-batch-id="this.selectedBatch" />
            </v-card-text>
            <v-card-actions>
                <v-layout pb-3 pr-5 justify-end>
                    <v-btn @click="showDialog = false">{{ $t('actions.close') }}</v-btn>
                </v-layout>
            </v-card-actions>
        </v-card>
    </v-dialog>
    </div>
</template>

<script>

  import axios from 'axios'
  import {mapActions} from 'vuex'
  import AccessLogList from '../components/AccessLogList'
  import ImportBatchChart from '../components/ImportBatchChart'
  import {isoDateTimeFormat, parseDateTime} from '../libs/dates'

  export default {
    name: "ImportBatchesPage",
    components: {ImportBatchChart, AccessLogList},
    data () {
      return {
        batches: [],
        showDialog: false,
        selectedBatch: null,
        loading: false,
        dialogType: 'data',
      }
    },
    computed: {
      headers () {
        return [
          {
            text: this.$i18n.t('title_fields.id'),
            value: 'pk'
          },
          {
            text: this.$i18n.t('labels.date'),
            value: 'created'
          },
          {
            text: this.$i18n.t('organization'),
            value: 'organization'
          },
          {
            text: this.$i18n.t('platform'),
            value: 'platform'
          },
          {
            text: this.$i18n.t('labels.report_type'),
            value: 'report_type'
          },
          {
            text: this.$i18n.t('labels.user'),
            value: 'user',
          },
          {
            text: this.$i18n.t('title_fields.actions'),
            value: 'actions',
            sortable: false,
          },
        ]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadImportBatches () {
        this.loading = true
        try {
          let response = await axios.get('/api/import-batch/')
          this.batches = response.data.results
          this.batches = this.batches.map(item => {item.created = isoDateTimeFormat(parseDateTime(item.created)); return item})
        } catch (error) {
          this.showSnackbar({content: 'Error loading title: ' + error})
        } finally {
          this.loading = false
        }
      },
    },
    mounted () {
      this.loadImportBatches()
    }
  }
</script>

<style scoped>

</style>
