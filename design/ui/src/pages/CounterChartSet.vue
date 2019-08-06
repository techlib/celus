<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-layout column>
        <v-flex>
            <v-select
                    :items="reportTypes"
                    item-text="name"
                    item-value="short_name"
                    v-model="selectedReportType"
                    :label="$t('available_report_types')"
            >
            </v-select>
        </v-flex>

        <v-flex class="mt-3 mb-3">
            <v-btn-toggle v-model="chartTypeIndex" mandatory>
                <v-btn v-for="(chartType, index) in chartTypes " flat :value="index" :key="index">
                    {{ chartType.name }}
                </v-btn>
            </v-btn-toggle>
        </v-flex>
        <APIChart
                v-if="selectedReportType"
                :type="selectedChartType.type === undefined ? 'histogram' : selectedChartType.type"
                :report-type-name="selectedReportType"
                :primary-dimension="selectedChartType.primary"
                :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                :organization="organizationForChart"
                :platform="platformId"
                :title="titleId"
                :extend="chartExtend"
                :stack="this.selectedChartType.stack === undefined ? true : this.selectedChartType.stack"
        >
        </APIChart>
        <div v-else>
                {{ $t('no_reports_available_for_title') }}
        </div>
    </v-layout>
</template>
<script>
  import APIChart from '../components/APIChart'
  import { mapGetters } from 'vuex'
  import axios from 'axios'

  export default {
    name: 'CounterChartSet',
    components: {APIChart},
    props: {
      chartExtend: {},
      platformId: {},
      titleId: {},
      reportTypesUrl: {},
      extraChartTypes: {
        default: () => [],
      }
    },
    data () {
      return {
        chartTypeIndex: 0,
        reportTypes: [], // report types available for this title
        selectedReportType: null,
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
        dateRangeStartText: 'dateRangeStartText',
        dateRangeEndText: 'dateRangeEndText',
      }),
      chartTypes () {
        let base = [
          {name: this.$i18n.t('chart.date_metric'), primary: 'date', secondary: 'metric', type: 'histogram', stack: false},
          {name: this.$i18n.t('chart.metric'), primary: 'metric'},
          {name: this.$i18n.t('chart.organization'), primary: 'organization', type: 'bar'},
        ]
        let extra = [
          {name: this.$i18n.t('chart.accesstype'), primary: 'Access_Type'},
          {name: this.$i18n.t('chart.accessmethod'), primary: 'Access_Method'},
          {name: this.$i18n.t('chart.datatype'), primary: 'Data_Type'},
          {name: this.$i18n.t('chart.sectiontype'), primary: 'Section_Type'},
          {name: this.$i18n.t('chart.yop'), primary: 'YOP'},
        ]
        let reportType = this.selectedReportTypeObject
        if (reportType) {
          let dimNames = reportType.dimensions_sorted.map(dim => dim.short_name)
          for (let option of extra) {
            if (dimNames.indexOf(option.primary) >= 0) {
              base.push(option)
            }
          }
        }
        this.extraChartTypes.map(item => base.push(item))
        return base
      },
      organizationForChart () {
        /* which organization should be reported to the APIChart component
        * - in case we want to compare organizations, we should not add organization to
        * the filter */
        if (this.selectedChartType.primary === 'organization') {
          return null
        }
        return this.selectedOrganization.pk
      },
      selectedReportTypeObject () {
        for (let rt of this.reportTypes) {
          if (rt.short_name === this.selectedReportType)
            return rt
        }
        return null
      },
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      },
    },
    methods: {
      async loadReportTypes () {
        let url = this.reportTypesUrl
        if (url) {
          try {
            const response = await axios.get(url)
            this.reportTypes = response.data
            this.selectFreshestReportType()
          } catch (error) {
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      selectFreshestReportType () {
        // selects the reportType that has the newest data but at the same time
        // is contained within the selected time period, so that it would not happen
        // that we would show an empty chart
        let bestReportType = null
        // select the freshest from those that overlap with current date selection
        for (let rt of this.reportTypes) {
          if ((bestReportType === null || rt.newest_log > bestReportType.newest_log) &&
              rt.oldest_log < this.dateRangeEndText &&
              rt.newest_log > this.dateRangeStartText) {
            bestReportType = rt
          }
        }
        // if nothing was selected and there are some reports, select the first one
        if (bestReportType === null && this.reportTypes.length > 0) {
          bestReportType = this.reportTypes[0]
        }
        if (bestReportType) {
          this.selectedReportType = bestReportType.short_name
        } else {
          this.selectedReportType = null
        }
      }
    },
    mounted () {
      this.loadReportTypes()
    }
  }
</script>
