<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <h3 class="mb-4"><span class="thin">{{ $t('platform') }}</span> {{ platform ? platform.name : '' }}</h3>
        <h2 class="mb-4"><span class="thin">{{ $t('title') }}</span> {{ title ? title.name : '' }}</h2>

        <section v-if="selectedOrganization && platformId && titleId">
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
                :platform="platformId"
                :title="titleId"
            >
        </APIChart>
        </section>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import TitleList from '../components/TitleList'
  import APIChart from '../components/APIChart'
  import axios from 'axios'

  export default {
    name: 'TitleDetailPage',
    components: {
      APIChart,
      TitleList,
    },
    props: {
      'platformId': {required: true, type: Number},
      'titleId': {required: true, type: Number},
      'platformData': {required: false},
    },
    data () {
      return {
        title: null,
        platformDataLocal: null,
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
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platform.pk}/title/`
        }
        return null
      },
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      },
      platform () {
        if (this.platformData) {
          return this.platformData
        }
        return this.platformDataLocal
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadTitle () {
        if (this.selectedOrganization && this.platformId && this.titleId) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}`)
            .then(response => {
              this.title = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading title: '+error})
            })
        }
      },
      loadPlatform () {
        if (this.selectedOrganization) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`)
            .then(response => {
              this.platformDataLocal = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: '+error})
            })
        }
      }
    },
    created () {
      if (!this.platformData) {
        this.loadPlatform()
      }
      this.loadTitle()
    },
    watch: {
      selectedOrganization () {
        this.loadPlatform()
        this.loadTitle()
      },
    }
  }
</script>

<style scoped type="scss">

    .thin {
        font-weight: 300;
    }

</style>
