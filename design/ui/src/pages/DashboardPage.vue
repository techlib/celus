<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
    total_interest: Total interest
    number_of_days: Number of days with data
    interest_per_day: Average daily interest
    title_interest_histogram: Interest histogram
    log: Logarithmic scale
    title_count: Resource count
    histogram_tooltip: SUSHI data very seldom contains data about titles for which there was no
      access recorded, so titles with zero count are likely heavily underrepresented.

cs:
    total_interest: Celkový zájem
    number_of_days: Počet dní s daty
    interest_per_day: Průměrný denní zájem
    title_interest_histogram: Histogram zájmu
    log: Logaritmická škála
    title_count: Počet zdrojů
    histogram_tooltip: SUSHI data zřídka obsahují informace o titulech, pro které nebyl zaznamenán
      žádný zájem. Z toho důvodu je počet titulů s nulovým zájmem pravděpodobně silně podhodnocen.
</i18n>

<template>
    <IntroPage v-if="loggedIn && showIntro" />
    <v-container fluid v-else-if="organizationId" pa-0 pa-sm-2>
        <!--v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row-->
        <v-row>
            <v-col cols="12" lg="6">
                <v-card min-height="480">
                    <v-card-title v-text="$t('interest')" class="float-left"></v-card-title>
                    <v-card-text class="pt-3">
                        <APIChart
                                v-if="interestReportType"
                                :organization="organizationId"
                                primary-dimension="date"
                                :report-type-id="interestReportType.pk"
                                secondary-dimension="Interest_Type"
                                raw-report-type
                                stack
                        >
                        </APIChart>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="12" lg="6">
                <v-card min-height="480">
                    <v-card-title>
                        <span v-text="$t('title_interest_histogram')"></span>
                        <v-spacer></v-spacer>
                        <v-tooltip bottom max-width="400px">
                            <template #activator="{on}">
                                <v-icon class="ml-2" v-on="on">fa fa-info-circle</v-icon>
                            </template>
                            {{ $t('histogram_tooltip') }}
                        </v-tooltip>

                    </v-card-title>
                    <v-card-text>
                        <div v-if="histogramChartData" style="position: relative">
                            <v-checkbox v-model="histogramLogScale" :label="$t('log')" style="position: absolute; bottom: 0; left: 1rem; z-index: 1" />
                            <ve-histogram

                                    :data="histogramChartData"
                                    :xAxis="{type: 'category', axisLabel: { rotate: 90 }, data: histogramChartXAxisData}"
                                    :yAxis="{type: histogramLogScale ? 'log' : 'value', min: histogramLogScale ? 0.1 : 0}"
                                    :settings="{labelMap: {'count': this.$t('title_count') }}"
                                    height="400px"
                            >
                            </ve-histogram>
                        </div>
                        <LoaderWidget v-else height="400px" />

                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
        <v-row class="align-stretch">

            <v-col cols="auto">
                <v-card height="100%" min-height="320">
                    <v-card-text>
                        <div v-if="totalInterestData" class="text-center ma-5">
                            <div v-text="$t('total_interest')"></div>
                            <div class="large-number" v-text="formatInteger(totalInterestData.interest_sum)"></div>
                            <div class="mt-8" v-text="$t('number_of_days')"></div>
                            <div class="big-number" v-text="formatInteger(totalInterestData.days)"></div>
                            <div class="mt-8" v-text="$t('interest_per_day')"></div>
                            <div class="large-number" v-text="smartFormatFloat(totalInterestData.interest_sum / totalInterestData.days)"></div>
                        </div>
                        <LargeSpinner v-else />
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col
                    cols="auto"
                    v-for="interestGroup in this.interestGroupTitlesSorted"
                    :key="interestGroup.short_name"
                    class="top-col"
            >
                <v-lazy
                    min-height="320"
                    transition="fade-transition"
                  >
                <TopTenDashboardWidget
                        :url-base="titleInterestBaseUrl"
                        :interest-group="interestGroup"
                        :pub-types="pubTypesForInterestGroup(interestGroup.short_name)"
                >

                </TopTenDashboardWidget>
                </v-lazy>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>

  import APIChart from '../components/APIChart'
  import {mapActions, mapGetters, mapState} from 'vuex'
  import axios from 'axios'
  import LargeSpinner from '../components/LargeSpinner'
  import {formatInteger, smartFormatFloat} from '../libs/numbers'
  import VeHistogram from 'v-charts/lib/histogram.common'
  import LoaderWidget from '../components/LoaderWidget'
  import {pubTypes} from '../libs/pub-types'
  import TopTenDashboardWidget from '../components/TopTenDashboardWidget'
  import IntroPage from './IntroPage'

  export default {
    name: "DashboardPage",

    components: {
      IntroPage,
      TopTenDashboardWidget,
      LargeSpinner,
      APIChart,
      VeHistogram,
      LoaderWidget,
    },

    data () {
      return {
        interestReportType: null,
        totalInterestData: null,
        histogramData: null,
        histogramLogScale: false,
      }
    },

    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
        interestGroups: state => state.interest.interestGroups,
      }),
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        loggedIn: 'loggedIn',
        showIntro: 'showIntro',
      }),
      interestGroupTitlesSorted () {
        let igs = this.interestGroups.filter(item => item.short_name !== 'other')
        if (igs) {
          return igs.sort((a, b) => (a.important === b.important) ? a.name > b.name : a.important < b.important)
        }
        return igs
      },
      titleInterestBaseUrl () {
        if (this.organizationId) {
          return `/api/organization/${this.organizationId}/title-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&page_size=10&desc=true&page=1`
        }
        return null
      },
      totalInterestDataUrl () {
        if (this.organizationId) {
          return `/api/organization/${this.organizationId}/interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      histogramDataUrl () {
        if (this.organizationId) {
          return `/api/organization/${this.organizationId}/title-interest-histogram/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      histogramChartData () {
        if (this.histogramData) {
          return {
            columns: ['name', 'count'],
            rows: this.histogramData,
          }
        }
        return null
      },
      histogramChartXAxisData () {
        return [...new Set(this.histogramData.map(item => item.name))]
      },
    },

    methods: {
      ...mapActions({
        fetchInterestReportType: 'fetchInterestReportType',
        showSnackbar: 'showSnackbar',
      }),
      formatInteger,
      smartFormatFloat,
      async fetchReportTypes() {
        this.interestReportType = await this.fetchInterestReportType()
      },

      async fetchTotalInterest() {
        if (this.totalInterestDataUrl) {
          try {
            const response = await axios.get(this.totalInterestDataUrl)
            this.totalInterestData = response.data
          } catch (error) {
            this.showSnackbar({
              content: 'Error loading total interest data: ' + error,
              color: 'error'
            })
          }
        }
      },

      async fetchHistogramData() {
        if (this.histogramDataUrl) {
          try {
            const response = await axios.get(this.histogramDataUrl)
            this.histogramData = response.data
          } catch (error) {
            this.showSnackbar({
              content: 'Error loading histogram data: ' + error,
              color: 'error'
            })
          }
        }
      },

      pubTypesForInterestGroup (igShortName) {
        if (igShortName.indexOf('full_text') > -1) {
          let all = {text: 'pub_type.all', value: '', icon: 'fa-expand'}
          return [
            all,
            ...pubTypes.filter(item => 'BJ'.indexOf(item.code) > -1)
              .map(item => {return {text: item.title, icon: item.icon, value: item.code}})
          ]
        }
        return []
      }
    },

    mounted () {
      this.fetchReportTypes()
      this.fetchTotalInterest()
      this.fetchHistogramData()
    },

    watch: {
      totalInterestDataUrl () {
        this.totalInterestData = null
        this.fetchTotalInterest()
      },
      histogramDataUrl () {
        this.histogramData = null
        this.fetchHistogramData()
      }
    }

  }
</script>

<style scoped lang="scss">

    table.dashboard {
        width: 100%;

        th {
            text-align: left;
            padding-right: 1rem;
        }

        td {
            text-align: right;
        }
    }

    div.large-number {
        font-size: 1.75rem;
        margin-top: 0.375rem;
        font-weight: bold;
    }

    div.big-number {
        font-size: 1.375rem;
        margin-top: 0.25rem;
        font-weight: bold;
    }

    .top-col {
        min-width: 400px;
    }

</style>
