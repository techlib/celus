<i18n src="../locales/charts.yaml"></i18n>

<template>
   <v-btn-toggle v-model="chartTypeIndex" mandatory class="flex-sm-wrap">
        <v-btn v-for="(chartType, index) in chartTypes " text :value="index" :key="chartType.pk">
            <v-tooltip bottom v-if="chartType.desc">
                    <template v-slot:activator="{ on }">
                        <span v-on="on" v-text="chartType.name"></span>
                    </template>
                    <span>{{ chartType.desc }}</span>
                </v-tooltip>
            <span v-else v-text="chartType.name"></span>
        </v-btn>
    </v-btn-toggle>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'

  export default {
    name: "ChartTypeSelector",
    props: {
      reportType: {required: true},
      value: {required: false, default: null},  // the selected chart type
    },
    data () {
      return {
        chartTypes: [],
        chartTypeIndex: null,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStartText: 'dateRangeStartText',
        dateRangeEndText: 'dateRangeEndText',
      }),
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadChartTypes () {
        if (this.reportType !== null) {
          try {
            let response = await axios.get(`/api/report-data-view/${this.reportType.pk}/chart-definitions/`)
            this.chartTypes = response.data
            if (this.chartTypes.length > 0) {
              this.chartTypeIndex = 0
            } else {
              this.chartTypeIndex = null
            }
          } catch (error) {
            this.showSnackbar({content: 'Error loading chart types: ' + error, color: 'error'})
          }
        } else {
          this.chartTypes = []
          this.chartTypeIndex = null
        }
      }
    },
    watch: {
      chartTypeIndex () {
        this.$emit('input', this.selectedChartType)
      },
      reportType () {
        this.chartTypes = []
        this.chartTypeIndex = null
        this.loadChartTypes()
      }
    },
    mounted () {
      this.loadChartTypes()
    }
  }
</script>

<style scoped>

</style>
