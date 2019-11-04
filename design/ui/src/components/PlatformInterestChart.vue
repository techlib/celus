<template>
    <VeBar
            :data="chartData"
            :settings="chartSettings"
            :height="height"
    />
</template>

<script>
  import { mapState } from 'vuex'
  import VeBar from 'v-charts/lib/bar.common'

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
      }
    }
  }
</script>

<style scoped>

</style>
