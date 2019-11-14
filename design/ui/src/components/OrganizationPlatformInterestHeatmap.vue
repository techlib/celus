<i18n>
en:
    chart_height: Chart height
cs:
    chart_height: Výška grafu
</i18n>

<template>
    <v-container fluid>
        <v-row no-gutters>
            <v-col cols="auto">
                <slot></slot>
            </v-col>
            <v-spacer></v-spacer>
            <v-col :cols="12" :sm="8" :lg="5" :xl="3" :md="7" class="pt-1">
                <v-slider
                        :max="maxHeight"
                        :min="minHeight"
                        v-model="height"
                        :label="$t('chart_height')"
                        dense
                        hide-details
                >
                    <template v-slot:thumb-label="{value}">
                        <span v-text="Math.round(100 * value / autoHeight) + '%'"></span>
                    </template>
                </v-slider>
            </v-col>
            <v-col cols="auto">
                <v-btn @click="height = autoHeight" dark color="primary">
                    <v-icon small>fa fa-redo-alt</v-icon>
                </v-btn>
            </v-col>
        </v-row>
        <v-row no-gutters>
            <v-col :cols="12">
                <ve-heatmap
                        :data="chartData"
                        :settings="chartSettings"
                        :height="heightString"
                        :xAxis="xAxis"
                >
                </ve-heatmap>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import VeHeatmap from 'v-charts/lib/heatmap.common'
  import { mapActions, mapGetters } from 'vuex'
  import axios from 'axios'

  export default {
    name: 'OrganizationPlatformInterestHeatmap',
    components: {
      VeHeatmap,
    },
    data () {
      return {
        dataRaw: [],
        loading: false,
        primaryDim: 'platform',
        secondaryDim: 'organization',
        reportTypeId: null,
        height: 200,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
      }),
      dataURL () {
        if (this.reportTypeId) {
          return `/api/chart-data-raw/${this.reportTypeId}/?prim_dim=${this.primaryDim}&sec_dim=${this.secondaryDim}&start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      columns () {
        if (this.loading)
          return []
        return [this.primaryDim, this.secondaryDim, 'count']
      },
      chartData () {
        return {
            columns: this.columns,
            rows: this.rows,
        }
      },
      rows () {
        return this.dataRaw
      },
      chartSettings () {
        return {
          yAxisList: [...new Set(this.dataRaw.map(item => item[this.secondaryDim]))].sort((a,b) => -a.localeCompare(b)),
          xAxisList: [...new Set(this.dataRaw.map(item => item[this.primaryDim]))].sort(),
        }
      },
      xAxis () {
        return {
          type: 'category',
          axisLabel: {
            rotate: 90,
          },
          splitArea: {
            show: true,
          },
          data: [...new Set(this.dataRaw.map(item => item[this.primaryDim]))].sort(),
        }
      },
      autoHeight () {
        const primDimUniqueValues = new Set(this.dataRaw.map(item => item[this.secondaryDim]))
        return this.dataRaw ? primDimUniqueValues.size * 18 + 100 : 200
      },
      minHeight () {
        return 200
      },
      maxHeight () {
        return this.autoHeight * 1.25
      },
      heightString () {
        return this.height.toString() + 'px'
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async fetchData () {
        if (this.dataURL) {
          this.loading = true
          try {
            const response = await axios.get(this.dataURL)
            this.dataRaw = response.data.data
            this.height = this.autoHeight
          } catch (error) {
            this.showSnackbar({content: 'Error loading data: ' + error, color: 'error'})
          } finally {
            this.loading = false
          }
        }
      },
      async fetchReportTypes () {
        try {
          const response = await axios.get('/api/report-type/')
          for (let rt of response.data) {
            if (rt.short_name === 'interest') {
              this.reportTypeId = rt.pk
              break
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading report types: ' + error, color: 'error'})
        }
      }
    },
    mounted () {
      this.fetchReportTypes()
    },
    watch: {
      dataURL () {
        this.fetchData()
      }
    }
  }
</script>

<style scoped>

</style>
