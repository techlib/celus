<i18n src="../locales/charts.yaml"></i18n>

<template>
    <VeBar
            :data="chartData"
            :settings="chartSettings"
            :height="height"
            :toolbox="chartToolbox"
    />
</template>

<script>
  import { mapState } from 'vuex'
  import VeBar from 'v-charts/lib/bar.common'
  // the following import is here to ensure the component at hand will be bundled
  import _toolBox from 'echarts/lib/component/toolbox'

  export default {
    name: 'PlatformInterestChart',
    components: {VeBar},
    props: {
      platforms: {type: Array, required: true},
    },
    computed: {
      ...mapState({
        interestGroups: state => state.interest.interestGroups,
      }),
      chartData () {
        return {
            columns: this.columns,
            rows: this.rows,
        }
      },
      columns () {
        return ['name', ...this.interestGroups.map(ig => ig.short_name)]
      },
      rows () {
        let rows = this.platforms.map(platform => {return {name: platform.name, ...platform.interests}})
        rows.reverse()
        return rows
      },
      chartSettings () {
        let labelMap = {}
        this.interestGroups.map(ig => labelMap[ig.short_name] = ig.name)
        return {
          stack: {'all': this.interestGroups.map(ig => ig.short_name)},
          labelMap: labelMap,
        }
      },
      height () {
        return 160 + this.platforms.length * 18 + 'px'
      },
      chartToolbox () {
        return {
          feature: {
            saveAsImage: {
              show: true,
              title: this.$t('chart.toolbox.save_as_image'),
              excludeComponents: ['toolbox'],
            },
          }
        }
      },
    }
  }
</script>

<style scoped>

</style>
