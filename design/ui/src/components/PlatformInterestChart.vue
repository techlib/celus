<i18n lang="yaml" src="../locales/charts.yaml"></i18n>

<template>
    <v-container>
        <v-row>
            <v-col cols="auto">
                <v-checkbox
                        v-model="logScale"
                        :label="$t('chart.log_scale')"
                        class="mt-1 ml-4"
                ></v-checkbox>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto">
                <slot></slot>
            </v-col>
        </v-row>
        <v-row no-gutters>
            <v-col>
                <VeBar
                        :data="chartData"
                        :settings="chartSettings"
                        :height="height"
                        :toolbox="chartToolbox"
                        :xAxis="{type: this.logScale ? 'log' : 'value'}"
                        :data-zoom="dataZoom"
                />
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import { mapState } from 'vuex'
  import VeBar from 'v-charts/lib/bar.common'
  // the following import is here to ensure the component at hand will be bundled
  import _toolBox from 'echarts/lib/component/toolbox'
  import _dataZoom from 'echarts/lib/component/dataZoom'

  export default {
    name: 'PlatformInterestChart',
    components: {VeBar},
    props: {
      platforms: {type: Array, required: true},
    },
    data () {
      return {
        logScale: false,
      }
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
        if (this.logScale) {
          return {
            labelMap: labelMap,
          }
        }
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
      dataZoom () {
        if (this.logScale) {
          return []
        }
        return [
          {
            type: 'slider',
            start: 0,
            end: 100,
            xAxisIndex: 0,
          },
        ]
      },
    }
  }
</script>

<style scoped>

</style>
