<i18n src="../locales/charts.yaml"></i18n>

<template>
   <v-btn-toggle v-model="chartTypeIndex" mandatory class="flex-sm-wrap">
        <v-btn v-for="(chartType, index) in chartTypes " text :value="index" :key="index">
            {{ chartType.name }}
        </v-btn>
    </v-btn-toggle>
</template>

<script>
  import {mapGetters, mapState} from 'vuex'

  export default {
    name: "ChartTypeSelector",
    props: {
      reportType: {required: true},
      value: {required: false, default: null},
      allowCrossReportCharts: {default: true},  // if chart types which do not have one specific report type are allowed
      allowInterestCharts: {default: true},  // should charts with interest in secondary dimension be allowed?
      extraChartTypes: {
        default: () => [],
      }
    },
    data () {
      return {
        chartTypeIndex: 0,
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
      chartTypes () {
        // check if the report type has a primary dimension
        if (this.reportType && this.reportType.primary_dimension) {
          let dim = this.reportType.primary_dimension
          return [
            {name: dim.name, primary: 'date', secondary: dim.short_name, type: 'histogram'},
          ]
        }
        let base = [
          {name: this.$i18n.t('chart.date_metric'), primary: 'date', secondary: 'metric', type: 'histogram', stack: false},
          {name: this.$i18n.t('chart.metric'), primary: 'metric'},
          {name: this.$i18n.t('chart.organization'), primary: 'organization', secondary: 'interest', type: 'bar', orderBy: 'count'},
        ]
        // only add interest_in_time in case no specific report type was selected
        if (this.reportType && this.reportType.pk === -1) {
          base.unshift({name: this.$i18n.t('chart.interest_in_time'), primary: 'date', secondary: 'interest', type: 'histogram', stack: false, reportType: null})
        }

        if (this.reportType && this.reportType.interest_only) {
          // shortcut for interest-only report types
          return base.filter(item => item.secondary === 'interest')
        }

        let extra = [
          {name: this.$i18n.t('chart.accesstype'), primary: 'Access_Type'},
          {name: this.$i18n.t('chart.accessmethod'), primary: 'Access_Method'},
          {name: this.$i18n.t('chart.datatype'), primary: 'Data_Type'},
          {name: this.$i18n.t('chart.sectiontype'), primary: 'Section_Type'},
          {name: this.$i18n.t('chart.yop'), primary: 'YOP', secondary: 'Data_Type', stack: true},
        ]
        let reportTypeSupportsInterest = false
        if (this.reportType) {
          let dimNames = this.reportType.dimensions_sorted.map(dim => dim.short_name)
          for (let option of extra) {
            if (dimNames.indexOf(option.primary) >= 0) {
              if (!option.secondary || dimNames.indexOf(option.secondary) >= 0)
                base.push(option)
            }
          }
          reportTypeSupportsInterest = this.reportType.interest_groups
        }
        this.extraChartTypes.map(item => base.push(item))

        return base.filter(item => this.allowCrossReportCharts || !('reportType' in item && item.reportType === null)).
          filter(item => (this.allowInterestCharts && reportTypeSupportsInterest || item.secondary !== 'interest'))
      },
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      },
    },
    watch: {
      chartTypeIndex () {
        this.$emit('input', this.selectedChartType)
      },
      reportType (value) {
        if (value !== null) {
          this.chartTypeIndex = 0
        }
        this.chartTypeIndex = null
      }
    },
    mounted () {
      this.$emit('input', this.selectedChartType)
    }
  }
</script>

<style scoped>

</style>
