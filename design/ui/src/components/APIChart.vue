<i18n src="../locales/common.yaml"></i18n>
<i18n src="../locales/charts.yaml"></i18n>

<template>
    <ve-histogram
            v-if="type === 'histogram'"
            :data="chartData"
            :settings="chartSettings"
            :extend="extend"
            :height="height"
            :loading="loading"
            :toolbox="chartToolbox"
            :data-zoom="dataZoom"
            >
    </ve-histogram>
    <ve-bar
            v-else-if="type === 'bar'"
            :data="chartData"
            :settings="chartSettings"
            :extend="extend"
            :height="height"
            :loading="loading"
            :toolbox="chartToolbox"
            :data-zoom="dataZoom"
        >
    </ve-bar>
    <ve-line
            v-else-if="type === 'line'"
            :data="chartData"
            :settings="chartSettings"
            :extend="extend"
            :height="height"
            :loading="loading"
            :toolbox="chartToolbox"
            :data-zoom="dataZoom"
        >
    </ve-line>
</template>
<script>
  import VeHistogram from 'v-charts/lib/histogram.common'
  import VeBar from 'v-charts/lib/bar.common'
  import VeLine from 'v-charts/lib/line.common'
  import axios from 'axios'
  import jsonToPivotjson from 'json-to-pivot-json'
  import { mapActions, mapGetters } from 'vuex'

  export default {
    name: 'APIChart',
    components: {VeHistogram, VeBar, VeLine},
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
      reportTypeName: {
        required: true,
      },
      metric: {
        required: false,
      },
      title: {  // id of the title to filter on
        type: Number,
        required: false,
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
        default: true,
      },
      height: {},
    },
    data () {
      return {
        data_raw: [],
        data_meta: null,
        loading: true,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
      }),
      dataURL () {
        let url = `${this.dataURLBase}chart-data/${this.reportTypeName}/?prim_dim=${this.primaryDimension}&start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        if (this.secondaryDimension) {
          url += `&sec_dim=${this.secondaryDimension}`
        }
        if (this.platform)
          url += `&platform=${this.platform}`
        if (this.organization)
          url += `&organization=${this.organization}`
        if (this.title)
          url += `&target=${this.title}`
        return url
      },
      columns () {
        if (this.loading)
          return []
        if (this.data_raw.length === 0)
          return []
        if (this.secondaryDimension) {
          let rows = this.rows
          return [
            this.dimensionToName(this.primaryDimension),
            ...Object.keys(rows[0]).filter(item => item !== this.primaryDimension)
          ]
        } else {
          return [this.dimensionToName(this.primaryDimension), 'count']
        }
      },
      chartData () {
        return {
            columns: this.columns,
            rows: this.rows,
        }
      },
      rows () {
        if (this.secondaryDimension) {
          return jsonToPivotjson(
            this.data_raw,
            {
              row: this.primaryDimension,
              column: this.secondaryDimension,
              value: 'count',
            })
        }
        return this.data_raw
      },
      chartSettings () {
        let out = {}
        if (!this.secondaryDimension) {
          // count is the metric, we remap it to a different name
          out['labelMap'] = {
            'count': this.$i18n.t('chart.count')
          }
        } else {
          if (this.rows && this.rows.length && this.stack) {
            out['stack'] = {
              'all': [...Object.keys(this.rows[0]).filter(item => item !== this.primaryDimension)]
            }
          }
        }
        return out
      },
      chartToolbox () {
        return {
          feature: {
            saveAsImage: {
              show: true,
              title: this.$t('chart.toolbox.save_as_image'),
            },
            dataZoom : {
              show : true,
              title : {
                zoom : this.$t('chart.toolbox.zoom'),
                back : this.$t('chart.toolbox.zoom_back'),
              }
            },
          }
        }
      },
      dataZoom () {
        return [{
          type: 'slider',
          start: 0,
          end: 100,
          //height: 20,
          //handleSize: 20,
        }]
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadData() {
        this.loading = true
        this.data_raw = []
        if (this.dataURL) {
          axios.get(this.dataURL)
            .then((response) => {
              this.data_raw = response.data.data
              this.loading = false
            }, (error) => {
              this.showSnackbar({content: 'Error fetching data: '+error})
              this.loading = false
            })
        }
      },
      dimensionToName (dim) {
        if (typeof dim === 'number') {
          return 'dim' + dim
        }
        return dim
      }
    },
    created () {
      this.loadData()
    },
    watch: {
      primaryDimension () {
        this.loadData()
      },
      secondaryDimension () {
        this.loadData()
      },
      dateRangeStart () {
        this.loadData()
      },
      dateRangeEnd () {
        this.loadData()
      },
      reportTypeName () {
        this.loadData()
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

</style>
