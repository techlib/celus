<template>
    <v-layout v-if="importBatch !== null" column>
        <v-flex pb-4>
            <ChartTypeSelector
                    :report-type="importBatch.report_type"
                    :allow-interest-charts="false"
                    v-model="selectedChartType"/>
        </v-flex>
        <v-flex>
            <APIChart
                v-if="selectedChartType"
                :type="selectedChartType.type === undefined ? 'histogram' : selectedChartType.type"
                :report-type-id="selectedChartType.reportType === null ? null : importBatch.report_type.pk"
                :primary-dimension="selectedChartType.primary"
                :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                :platform="importBatch.platform.pk"
                :stack="selectedChartType.stack === undefined ? true : selectedChartType.stack"
                :order-by="selectedChartType.orderBy === undefined ? null : selectedChartType.orderBy"
                :import-batch="importBatch.pk"
            />
        </v-flex>
</v-layout>
</template>

<script>
  import ChartTypeSelector from './ChartTypeSelector'
  import APIChart from './APIChart'
  import axios from 'axios'
  import {mapActions} from 'vuex'
  export default {
    name: "ImportBatchChart",
    components: {APIChart, ChartTypeSelector},
    props: {
      importBatchId: {required: true},
    },
    data () {
      return {
        selectedChartType: null,
        importBatch: null,
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
      }
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
