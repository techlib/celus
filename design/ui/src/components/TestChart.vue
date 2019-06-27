<template>
    <v-layout row wrap>
        <v-flex xs12>
            <v-select
                    v-model="selectedReportType"
                    :items="reportTypes"
                    label="report type"
                    required
            >
                <template v-slot:item="{item}">
                    <span>{{ item.name }}</span>
                </template>
                <template v-slot:selection="{item}">
                    <span>{{ item.name }}</span>
                </template>
            </v-select>
        </v-flex>
        <v-flex sm4
        >
            <v-select
                    v-model="primaryDim"
                    :items="dimensions"
                    label="primary dimension"
                    required
            ></v-select>
            <v-select
                    v-model="secondaryDim"
                    :items="possibleSecondaryDims"
                    label="secondary dimension"
                    required
            ></v-select>
        </v-flex>
        <v-flex xs12 sm8>
            <ve-bar
                    v-if="type === 'bar'"
                    :data="chartData"
                    :settings="chart_settings_joined"
                    :series="series"
                    :extend="extend"
                    :height="height"
                    :loading="loading"
                    :events="events">
            </ve-bar>
        </v-flex>
    </v-layout>
</template>
<script>
  import VeBar from 'v-charts/lib/bar.common'
  import axios from 'axios'
  import jsonToPivotjson from 'json-to-pivot-json'
  import { mapActions } from 'vuex'

  export default {
    name: 'TestChart',
    components: {VeBar},
    props: {
      type: {
        type: String,
        default: 'bar',
      },
      series: {
        type: Array,
      },
      title: {
        type: String,
      },
      data_url_base: {
        type: String,
        default: '/api/logs/',
      },
      chart_settings: {},
      textPosition: {
        type: String,
        default: 'left'
      },
      extend: {
        type: Object,
        default: ret => {},
      },
      height: {},
      events: Object,
    },
    data () {
      return {
        data_raw: [],
        data_meta: null,
        loading: true,
        dimensions: ['date', 'platform', 'organization', 'metric', 'target'],
        primaryDim: 'date',
        secondaryDim: null,
        reportTypes: [],
        selectedReportType: null,
      }
    },
    computed: {
      dataURL () {
        let url = `${this.data_url_base}chart-data/${this.selectedReportType.short_name}/?prim_dim=${this.primaryDim}`
        if (this.secondaryDim) {
          url += `&sec_dim=${this.secondaryDim}`
        }
        return url
      },
      columns () {
        if (this.loading)
          return []
        if (this.secondaryDim) {
          let rows = this.rows
          return [this.primaryDim, ...Object.keys(rows[0]).filter(item => item !== this.primaryDim)]
        } else {
          return [this.primaryDim, 'count']
        }
      },
      chartData () {
        return {
            columns: this.columns,
            rows: this.rows,
        }
      },
      rows () {
        if (this.secondaryDim) {
          return jsonToPivotjson(
            this.data_raw,
            {
              row: this.primaryDim,
              column: this.secondaryDim,
              value: "count"
            })
        }
        return this.data_raw
      },
      chart_settings_joined () {
        let out = {}
        Object.assign(out, this.chart_settings)
        if (this.data_meta) {
          Object.assign(out, this.data_meta)
        }
        return out
      },
      possiblePrimaryDims () {
        return this.dimensions
      },
      possibleSecondaryDims () {
        return this.dimensions.filter(item => item !== this.primaryDim)
      },

    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      load_data() {
        this.loading = true
        this.data_raw = []
        if (this.dataURL) {
          axios.get(this.dataURL)
            .then((response) => {
              console.log(response.data.data);
              this.data_raw = response.data.data
              this.loading = false
            }, (error) => {
              this.showSnackbar({content: 'Error fetching data: '+error})
              console.log('Error fetching data', error)
              this.loading = false
            })
        }
      },
      loadReportTypes () {
        axios.get(this.data_url_base + 'report-type/')
          .then((response) => {
            this.reportTypes = response.data
            if (this.reportTypes.length) {
              this.$set(this, 'selectedReportType', this.reportTypes[0])
            }
          }, (error) => {
            this.showSnackbar({content: 'Error fetching data: '+error})
          }
        )
      },
    },
    watch: {
      data_url: function () {
        this.load_data()
      },
      primaryDim () {
        this.load_data()
      },
      secondaryDim () {
        this.load_data()
      },
      selectedReportType () {
        this.load_data()
      }
    },
    created() {
      this.loadReportTypes()
      // this.load_data()
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
