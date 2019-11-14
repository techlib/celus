<template>
    <ve-heatmap
            :data="chartData"
            :settings="chartSettings"
            :height="height"
            :xAxis="xAxis"
    >
    </ve-heatmap>
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
        }
      },
      xAxis () {
        return {
          type: 'category',
          axisLabel: {
            rotate: 90,
          },
          data: [...new Set(this.dataRaw.map(item => item[this.primaryDim]))].sort(),
        }
      },
      height () {
        const primDimUniqueValues = new Set(this.dataRaw.map(item => item[this.secondaryDim]))
        return (this.dataRaw ? primDimUniqueValues.size * 18 + 100 : 200).toString() + 'px'
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
