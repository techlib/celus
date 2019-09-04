<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-layout column>
        <v-flex>
            <v-select
                    :items="reportTypes"
                    item-text="name"

                    v-model="selectedReportTypeObject"
                    :label="$t('available_report_types')"
                    :return-object="true"
            >
            </v-select>
        </v-flex>

        <v-flex class="mt-3 mb-3">
            <ChartTypeSelector
                    :extra-chart-types="extraChartTypes"
                    :report-type="selectedReportTypeObject"
                    v-model="selectedChartType"/>
        </v-flex>
        <APIChart
                v-if="selectedReportType && selectedChartType"
                :type="selectedChartType.type === undefined ? 'histogram' : selectedChartType.type"
                :report-type-id="selectedChartType.reportType === null ? null : selectedReportType"
                :primary-dimension="selectedChartType.primary"
                :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                :organization="organizationForChart"
                :platform="platformId"
                :title="titleId"
                :extend="chartExtend"
                :stack="this.selectedChartType.stack === undefined ? true : this.selectedChartType.stack"
                :order-by="this.selectedChartType.orderBy === undefined ? null : this.selectedChartType.orderBy"
                :virtual="selectedReportTypeObject.virtual"
        >
        </APIChart>
        <div v-else>
                {{ $t('no_reports_available_for_title') }}
        </div>
    </v-layout>
</template>
<script>
  import APIChart from './APIChart'
  import { mapGetters, mapState } from 'vuex'
  import axios from 'axios'
  import ChartTypeSelector from './ChartTypeSelector'

  export default {
    name: 'CounterChartSet',
    components: {APIChart, ChartTypeSelector},
    props: {
      chartExtend: {},
      platformId: {},
      titleId: {},
      reportTypesUrl: {},
      virtualReportTypesUrl: {},
      extraChartTypes: {
        default: () => [],
      }
    },
    data () {
      return {
        chartTypeIndex: 0,
        reportTypes: [], // report types available for this title
        selectedReportTypeObject: null,
        selectedChartType: null,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStartText: 'dateRangeStartText',
        dateRangeEndText: 'dateRangeEndText',
      }),
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
        lang: 'appLanguage',
      }),
      organizationForChart () {
        /* which organization should be reported to the APIChart component
        * - in case we want to compare organizations, we should not add organization to
        * the filter */
        if (this.selectedChartType.primary === 'organization') {
          return null
        }
        if (this.selectedOrganizationId === -1) {
          return null  // we want data for all organizations
        }
        return this.selectedOrganizationId
      },
      selectedReportType () {
        if (this.selectedReportTypeObject)
          return this.selectedReportTypeObject.pk
        return null
      },
    },
    methods: {
      async loadReportTypes () {
        let url = this.reportTypesUrl
        if (url) {
          try {
            const response = await axios.get(url)
            this.reportTypes = response.data
            if (this.reportTypes.filter(item => item.interest_groups).length > 0) {
              // there is at least one report defining interest, we add the 'Interest' option
              // and select it
              this.reportTypes.unshift({
                name: this.lang === 'cs' ? 'Souhrnný zájem' : 'Aggregated interest',
                pk: -1,
                dimensions_sorted: [],
                interest_only: true
              })
              this.selectedReportTypeObject = this.reportTypes[0]
            } else {
              this.selectFreshestReportType()
            }
            this.loadVirtualReportTypes()
          } catch (error) {
            console.log("ERROR: ", error)
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      async loadVirtualReportTypes () {
        let url = this.virtualReportTypesUrl
        if (url) {
          try {
            const response = await axios.get(url)
            for (let rt of response.data) {
              rt['virtual'] = true
              rt['dimensions_sorted'] = []
              this.reportTypes.push(rt)
            }
          } catch (error) {
            console.log("ERROR: ", error)
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
          this.selectedReportTypeObject = bestReportType
        } else {
          this.selectedReportTypeObject = null
        }
      }
    },
    watch: {
      selectedReportTypeObject () {
        this.chartTypeIndex = 0
      },
    },
    mounted () {
      this.loadReportTypes()
    }
  }
</script>
