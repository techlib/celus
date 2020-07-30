<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/charts.yaml"></i18n>

<template>
    <LoaderWidget
            v-if="loading || crunchingData"
            :height="height"
            :text="crunchingData ? crunchingText : $t('chart.loading_data')"
            icon-name="fa-cog"
    />
    <div v-else-if="tooMuchData" :style="{'height': height}" id="loading">
        <div>
            <i class="far fa-frown"></i>
            <div class="infotext">{{ $t('chart.too_much_data') }}</div>
        </div>
    </div>
    <div v-else-if="dataRaw.length === 0" :style="{'height': height}" id="loading">
        <div>
            <i class="far fa-frown"></i>
            <div class="infotext">{{ $t('chart.no_data') }}</div>
        </div>
    </div>
    <div v-else>
    <v-container class="pa-0" fluid>
        <v-row class="pb-3">
            <v-col
                    v-if="showTableToggle"
                    cols="auto"
                    class="pl-5 py-0"
            >
                <v-btn-toggle
                        v-model="tableView"
                        mandatory
                        borderless
                >
                    <v-tooltip bottom>
                        <template #activator="{on}">
                            <v-btn :value="false" small v-on="on">
                                <v-icon small>fa fa-chart-bar</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('chart_view.chart') }}</span>
                    </v-tooltip>
                    <v-tooltip bottom>
                        <template #activator="{on}">
                            <v-btn :value="true" small v-on="on">
                                <v-icon small>fa fa-list</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('chart_view.table') }}</span>
                    </v-tooltip>
                </v-btn-toggle>
            </v-col>
            <v-col
                    v-if="allowYearAsSeries"
                    cols="auto"
                    class="pl-5 py-0"
            >
                <v-btn-toggle
                        v-model="yearAsSeries"
                        mandatory
                        borderless
                >
                    <v-tooltip bottom>
                        <template #activator="{on}">
                            <v-btn :value="false" small v-on="on">
                                <v-icon x-small>fa fa-ellipsis-h</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('x_axis.linear') }}</span>
                    </v-tooltip>
                    <v-tooltip bottom>
                        <template #activator="{on}">
                            <v-btn :value="true" small v-on="on"  :disabled="primaryDimension !== 'date'">
                                <v-icon x-small>fa fa-layer-group</v-icon>
                            </v-btn>
                        </template>
                        <span>{{ $t('x_axis.year_months') }}</span>
                    </v-tooltip>
                </v-btn-toggle>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto" shrink class="pr-3 pa-0" v-if="reportedMetrics.length">
                <v-tooltip bottom>
                    <template #activator="{on}">
                        <span v-on="on">
                            <v-icon
                                    color="info"
                            >
                                fa-info-circle
                            </v-icon>
                        </span>
                    </template>
                    <strong>{{ $t('reported_metrics_tooltip') }}</strong>
                    <div v-html="reportedMetricsText"></div>
                    <span v-if="reportedMetrics.length > 1">{{ $t('reported_metrics_tooltip_many') }}</span>
                </v-tooltip>
            </v-col>
        </v-row>
    </v-container>
        <div :style="{'min-height': height}">
                <component
                        v-if="!tableView"
                        :is="chartComponent"
                        :data="chartData"
                        :settings="chartSettings"
                        :extend="chartExtend"
                        :height="height"
                        :toolbox="chartToolbox"
                        :data-zoom="dataZoom"
                        :mark-line="markLine"
                        >
                </component>
            <ChartDataTable
                    :rows="chartData.rows"
                    :columns="chartData.columns"
                    :primary-dimension="shownPrimaryDimension"
                    v-else>
            </ChartDataTable>
        </div>
    </div>
</template>
<script>
  import VeHistogram from 'v-charts/lib/histogram.common'
  import VeBar from 'v-charts/lib/bar.common'
  import VeLine from 'v-charts/lib/line.common'
  // the following two imports are here to ensure the components at hand will be bundled
  import _dataZoom from 'echarts/lib/component/dataZoom'
  import _toolBox from 'echarts/lib/component/toolbox'
  // other imports
  import axios from 'axios'
  import { mapActions, mapGetters, mapState } from 'vuex'
  import 'echarts/lib/component/markLine'
  import LoaderWidget from './LoaderWidget'
  import { pivot } from '../libs/pivot'
  import ChartDataTable from './ChartDataTable'

  export default {
    name: 'APIChart',
    components: {ChartDataTable, VeHistogram, VeBar, VeLine, LoaderWidget},
    props: {
      type: {
        type: String,
        default: 'histogram',
      },
      organization: {
        required: false,
      },
      platform: {
        required: false,
      },
      primaryDimension: {
        required: true,
      },
      secondaryDimension: {
        required: false,
      },
      reportTypeId: {
        required: true,
      },
      metric: {
        required: false,
      },
      title: {  // id of the title to filter on
        type: Number,
        required: false,
      },
      importBatch: {  // id of the Batch
        required: false,
        type: Number,
      },
      dataURLBase: {
        type: String,
        default: '/api/',
      },
      extend: {
        type: Object,
        default: ret => {},
      },
      stack: {
        type: Boolean,
        default: false,
      },
      height: {
        default: '400px'
      },
      zoom: {
        type: Boolean,
        default: true,
      },
      ignoreDateRange: {
        type: Boolean,
        default: false,
      },
      orderBy: {},
      showMarkLine: {default: true},
      rawReportType: {
        default: false,
        type: Boolean,
      },
      maxLabelLength: {
        default: 50,
        type: Number,
      },
      showTableToggle: {
        default: true,
        type: Boolean,
      },
      allowYearAsSeries: {
        default: true,
        type: Boolean,
      },
    },
    data () {
      return {
        dataRaw: [],
        loading: true,
        crunchingData: false,
        reportedMetrics: [],
        tooMuchData: false,
        displayData: [],
        rawDataLength: 0,
        rawData: null,
        out: null,
        tableView: false,
        yearAsSeries: false, // should each year form a separate series?
      }
    },
    computed: {
      ...mapState({
        user: 'user',
      }),
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        selectedOrganization: 'selectedOrganization',
      }),
      dataURL () {
        if (!this.user) {
          return null
        }
        let reportTypePart = ''  // used do decide if report type should be part of the URL
        if (this.reportTypeId && this.reportTypeId !== -1) {
            reportTypePart = `${this.reportTypeId}/`
        }
        let urlStart = this.rawReportType ? 'chart-data-raw' : 'chart-data'
        let url = `${this.dataURLBase}${urlStart}/${reportTypePart}?prim_dim=${this.primaryDimension}`
        if (!this.ignoreDateRange) {
          url += `&start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        if (this.secondaryDimension) {
          url += `&sec_dim=${this.secondaryDimension}`
        }
        if (this.platform)
          url += `&platform=${this.platform}`
        if (this.organization)
          url += `&organization=${this.organization}`
        if (this.title)
          url += `&target=${this.title}`
        if (this.importBatch)
          url += `&import_batch=${this.importBatch}`
        return url
      },
      columns () {
        if (this.loading)
          return []
        if (this.dataRaw.length === 0)
          return []
        if (this.shownSecondaryDimension) {
          let rows = this.rows
          return [
            this.dimensionToName(this.shownPrimaryDimension),
            ...Object.keys(rows[0]).filter(item => item !== this.shownPrimaryDimension)
          ]
        } else {
          return [this.dimensionToName(this.shownPrimaryDimension), 'count']
        }
      },
      chartData () {
        return {
            columns: this.columns,
            rows: this.rows,
        }
      },
      chartExtend () {
        let colors = ['#ff0000', '#ff8844', '#ff4488', '#ff4444']
        if (this.shownPrimaryDimension === 'organization') {
          let that = this
          return {
            series(item) {
              let organizationRowNum = that.organizationRow
              if (organizationRowNum !== null) {
                let serIdx = 0
                for (let ser of item) {
                  ser.data = ser.data.map((v, index) => ({
                    value: v,
                    itemStyle: {color: index === organizationRowNum ? colors[serIdx % 4] : null}
                  }))
                  serIdx++
                }
              }
              return item
            }
          }
        }
        return {}
      },
      markLine () {
        if (this.shownPrimaryDimension === 'organization' && this.showMarkLine && this.organizationRow !== null) {
          return {
            silent: true,
            symbol: ['none', 'none'],
            data: [
              {
                name: 'me',
                yAxis: this.organizationRow,
                lineStyle: {
                  normal: {
                    color: '#aa0010',
                    type: 'solid',
                    width: 1,
                  }
                },
                label: {
                  formatter: this.$t('chart.my_org'),
                  position: 'middle',
                }
              },
            ]
          }
        }
        return {}
      },
      rows () {
        if (this.loading || this.crunchingData) {
          return []
        }
        return this.displayData
      },
      organizationRow () {
        if (!this.selectedOrganization) {
          return null
        }
        let i = 0
        for (let row of this.rows) {
          if (row.organization === this.selectedOrganization.name) {
            return i
          }
          i++
        }
        return null
      },
      chartSettings () {
        let out = {}
        if (!this.shownSecondaryDimension) {
          // count is the metric, we remap it to a different name
          out['labelMap'] = {
            'count': this.$i18n.t('chart.count')
          }
        } else {
          if (this.rows && this.rows.length) {
            if (this.regroupByYear) {
              let stack = {}
              for (let key of Object.keys(this.rows[0])) {
                let year = key.substring(0, 4)
                if (!(year in stack)) {
                  stack[year] = []
                }
                stack[year].push(key)
              }
              out['stack'] = stack
            } else if (this.stack) {
              out['stack'] = {
                'all': [...Object.keys(this.rows[0]).filter(item => item !== this.shownPrimaryDimension)]
              }
            }
          }
        }
        return out
      },
      chartToolbox () {
        let toolbox = {
          feature: {
            saveAsImage: {
              show: true,
              title: this.$t('chart.toolbox.save_as_image'),
              excludeComponents: ['toolbox', 'dataZoom'],
            },
            myExportData: {
              show: true,
              title: this.$t('chart.toolbox.export_csv'),
              icon: 'path://m 434.57178,114.29929 -83.882,-83.882005 c -9.00169,-9.001761 -21.21063,-14.058933 -33.941,-14.059 H 48.630782 c -26.51,0 -47.9999996,21.49 -47.9999996,48 V 416.35829 c 0,26.51 21.4899996,48 47.9999996,48 H 400.63078 c 26.51,0 48,-21.49 48,-48 v -268.118 c -7e-5,-12.73037 -5.05724,-24.93931 -14.059,-33.941 z m -161.941,-49.941005 v 80.000005 h -128 V 64.358285 Z m -48,152.000005 c -48.523,0 -88,39.477 -88,88 0,48.523 39.477,88 88,88 48.523,0 88,-39.477 88,-88 0,-48.523 -39.477,-88 -88,-88 z',
              onclick: function (that) {
                return function () {
                  window.open(that.dataURL + '&format=csv')
                }
              }(this)
            }
          }
        }
        if (this.zoom && false) {  // temporarily disabled, there is bug in echarts - https://github.com/apache/incubator-echarts/issues/10972
          toolbox.feature['dataZoom'] = {
              show : true,
              title : {
                zoom : this.$t('chart.toolbox.zoom'),
                back : this.$t('chart.toolbox.zoom_back'),
              }
          }
        }
        return toolbox
      },
      dataZoom () {
        if (this.zoom) {
          return [
            {
              type: 'slider',
              start: 0,
              end: 100,
              yAxisIndex: this.type === 'bar' ? 0 : null,
            },
          ]
        } else {
          return []
        }
      },
      chartComponent () {
        if (this.type === 'bar') {
          return VeBar
        } else if (this.type === 'histogram') {
          return VeHistogram
        } else {
          return VeLine
        }
      },
      reportedMetricsText () {
        if (this.reportedMetrics.length > 0) {
          let inside = this.reportedMetrics.map(metric => (metric.name || metric.short_name).replace(/_/g, ' ')).join('</li><li>')
          return `<ul><li>${inside}</li></ul>`
        } else {
          return ''
        }
      },
      crunchingText () {
        return this.$tc('chart.crunching_records', this.rawDataLength)
      },
      regroupByYear () {
        return this.yearAsSeries && this.primaryDimension === 'date'
      },
      shownPrimaryDimension () {
        if (this.regroupByYear)
          return 'month'
        return this.primaryDimension
      },
      shownSecondaryDimension () {
        if (this.regroupByYear)
          return 'year'
        return this.secondaryDimension
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async ingestData (rawData) {
        // prepare the data
        this.crunchingData = true
        // reformat date value to exclude the day component
        // the check for dict.date.substring is there because the date may be a year as a number
        // in some cases
        rawData = rawData.map(dict => {if ('date' in dict && dict.date.substring) dict['date'] = dict.date.substring(0, 7); return dict})
        // truncate long labels
        this.dataRaw = rawData.map(dict => {
            let val1 = String(dict[this.primaryDimension])
            if (val1.length > this.maxLabelLength + 3) {
              dict[this.primaryDimension] = val1.substring(0, this.maxLabelLength) + '\u2026'
            }
            if (this.secondaryDimension) {
              let val2 = dict[this.secondaryDimension]
              if (val2.length > this.maxLabelLength + 3) {
                dict[this.secondaryDimension] = val2.substring(0, this.maxLabelLength) + '\u2026'
              }
            }
            return dict
          }
        )
        // extract years when necessary
        if (this.regroupByYear) {
          this.dataRaw.forEach(dict => {
            dict['year'] = dict['date'].substring(0, 4)
            if (this.secondaryDimension) {
              dict.year += ': ' + dict[this.secondaryDimension]
            }
            dict['month'] = Number.parseInt(dict['date'].substring(5, 7), 10)
          })
        }
        // secondary dimension
        if (this.shownSecondaryDimension) {
          let now = new Date()
          let out = this.pivot()
          this.out = out
          console.log('pivot ended', new Date() - now)
          if (this.orderBy) {
            // NOTE: order by sum of values - it does not matter how is the orderBy called
            function sumNonPrimary (rec) {
              // remove value of primary dimension, sum the rest
              return Object.entries(rec).filter(([a, b]) => a !== this.shownPrimaryDimension).map(([a, b]) => b).reduce((x, y) => x + y)
            }
            let sum = sumNonPrimary.bind(this)
            out.sort((a, b) => (sum(a) - sum(b)))
          }
          if (this.regroupByYear && this.shownPrimaryDimension === 'month') {
            out.forEach(dict => dict.month = new Date(2020, dict.month - 1, 1).toLocaleString(this.$i18n.locale,{month: "short"}))
          }
          this.displayData = out
        } else {
          // no secondary dimension
          if (this.orderBy) {
            // order by
            this.dataRaw.sort((a, b) => {
              return a[this.orderBy] - b[this.orderBy]
            })
          }
          this.displayData = this.dataRaw
        }
        this.crunchingData = false
      },
      async loadData() {
        this.loading = true
        this.dataRaw = []
        this.tooMuchData = false
        if (this.dataURL) {
          try {
            let response = await axios.get(this.dataURL)
            if (response.data.too_much_data) {
              this.tooMuchData = true
              return
            }
            this.loading = false
            this.crunchingData = true
            this.rawDataLength = response.data.data.length
            this.rawData = response.data.data
            this.reportedMetrics = response.data.reported_metrics
            // we use timeout to give the interface time to redraw
            setTimeout(async () => await this.ingestData(response.data.data), 10)
          } catch (error) {
            this.showSnackbar({content: 'Error fetching data: '+error, color: 'error'})
          } finally {
            this.loading = false
          }
        }
      },
      pivot () {
        return pivot(this.dataRaw, this.shownPrimaryDimension, this.shownSecondaryDimension, 'count')
      },
      dimensionToName (dim) {
        if (typeof dim === 'number') {
          return 'dim' + dim
        }
        return dim
      }
    },
    mounted () {
      this.loadData()
    },
    watch: {
      dataURL () {
        this.loadData()
      },
      yearAsSeries () {
        this.ingestData(this.rawData)
      }
    }
  }
</script>
<style scoped lang="scss">

    .accomp-text {
        font-size: 125%;
        text-align: center;

        &.left {
            padding-right: 0;
        }
        &.right {
            padding-left: 0;
        }

    }

    .chart {
        margin: 1rem;
    }

    #loading {
        font-size: 60px;
        color: #1db79a88;
        text-align: center;

        i {
            margin-top: 160px;
        }

        div.infotext {
            font-size: 26px;
        }
    }

</style>
