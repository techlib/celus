<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <h2 class="mb-4"><span class="thin">{{ $t('platform') }}</span> {{ platform ? platform.name : '' }}</h2>

        <section v-if="selectedOrganization && platform">
        <h3>{{ $t('overview') }}</h3>
        <div class="mt-3 mb-3">
            <v-btn-toggle v-model="chartTypeIndex" mandatory>
              <v-btn v-for="(chartType, index) in chartTypes " flat :value="index" :key="index">
                {{ chartType.name }}
              </v-btn>
            </v-btn-toggle>
        </div>

        <APIChart
                report-type-name="TR"
                :primary-dimension="selectedChartType.primary"
                :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                :organization="selectedOrganization.pk"
                :platform="platform.pk"
            >
        </APIChart>
        </section>

        <h3 class="pt-3">{{ $t('titles') }}</h3>
        <TitleList :url="titleListURL" :platform-id="platformId"></TitleList>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import TitleList from '../components/TitleList'
  import APIChart from '../components/APIChart'
  import axios from 'axios'

  export default {
    name: 'PlatformDetailPage',
    components: {
      APIChart,
      TitleList,
    },
    props: {
      'platformId': {required: true},
    },
    data () {
      return {
        platform: null,
        chartTypeIndex: 0,
        chartTypes: [
          {name: this.$i18n.t('chart.date_metric'), primary: 'date', secondary: 'metric'},
          {name: this.$i18n.t('chart.metric'), primary: 'metric'},
          {name: this.$i18n.t('chart.accesstype'), primary: 1},
          {name: this.$i18n.t('chart.accessmethod'), primary: 2},
          {name: this.$i18n.t('chart.datatype'), primary: 3},
          {name: this.$i18n.t('chart.sectiontype'), primary: 4},
        ]
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      }),
      titleListURL () {
        if (this.platform !== null) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platform.pk}/title-count/`
        }
        return null
      },
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadPlatform () {
        if (this.selectedOrganization) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`)
            .then(response => {
              this.platform = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: '+error})
            })
        }
      }
    },
    created () {
      this.loadPlatform()
    },
    watch: {
      selectedOrganization () {
        this.loadPlatform()
      }
    }
  }
</script>

<style scoped lang="scss">

    .thin {
        font-weight: 300;
    }

</style>
