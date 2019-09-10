<template>
<v-container>
    <v-row>
        <v-col>
            <CounterChartSet
                    v-if="importBatch"
                    :platform-id="importBatch.platform.pk"
                    :import-batch-id="importBatchId"
                    :report-views-url="reportViewsUrl"
                    ignore-organization
            />
        </v-col>
    </v-row>
</v-container>
</template>

<script>
  import ChartTypeSelector from './ChartTypeSelector'
  import APIChart from './APIChart'
  import CounterChartSet from './CounterChartSet'
  import axios from 'axios'
  import {mapActions} from 'vuex'
  export default {
    name: "ImportBatchChart",
    components: {APIChart, ChartTypeSelector, CounterChartSet},
    props: {
      importBatchId: {required: true},
    },
    data () {
      return {
        selectedChartType: null,
        importBatch: null,
      }
    },
    computed: {
      reportViewsUrl () {
        if (this.importBatch) {
          return `/api/report-type/${this.importBatch.report_type.pk}/report-views/`
        }
        return null
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadImportBatch () {
        try {
          let response = await axios.get(`/api/import-batch/${this.importBatchId}/`)
          this.importBatch = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading batch details: ' + error})
        }
      },
    },
    watch: {
      importBatchId () {
        this.loadImportBatch()
      }
    },
    mounted () {
      this.loadImportBatch()
    }
  }
</script>

<style scoped>

</style>
