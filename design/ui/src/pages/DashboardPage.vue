<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
    titles_with_most_interest: Titles with the most interest of this type
    no_matching_titles: No titles with this type of interest
    total_interest: Total interest
    number_of_days: Number of days with data
    interest_per_day: Average daily interest
    title_interest_histogram: Title interest histogram
    log: Logarithmic scale
    title_count: Title count
    histogram_tooltip: SUSHI data very seldom contains data about titles for which there was not
      access recorded, so titles with zero count are likely heavily underrepresented.

cs:
    titles_with_most_interest: Tituly s největším zájmem tohoto typu
    no_matching_titles: Žádné tituly pro tento typ zájmu
    total_interest: Celkový zájem
    number_of_days: Počet dní s daty
    interest_per_day: Průměrný denní zájem
    title_interest_histogram: Histogram zájmu o tituly
    log: Logaritmická škála
    title_count: Počet titulů
    histogram_tooltip: SUSHI data zřídka obsahují informace o titulech, pro které nebyl zaznamenán
      žádný zájem. Z toho důvodu je počet titulů s nulovým zájmem pravděpodobně silně podhodnocen.
</i18n>

<template>
    <v-container fluid v-if="organizationId">
        <!--v-row>
            <v-col>
                <h1 v-text="$t('pages.dashboard')"></h1>
            </v-col>
        </v-row-->
        <v-row>
            <v-col cols="12" lg="6">
                <v-card>
                    <v-card-title v-text="$t('interest')"></v-card-title>
                    <v-card-text>
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
                <v-card>
                    <v-card-title>
                        <span v-text="$t('title_interest_histogram')"></span>
                        <v-tooltip bottom max-width="400px">
                            <template #activator="{on}">
                                <v-icon class="ml-2" v-on="on">fa fa-info-circle</v-icon>
                            </template>
                            {{ $t('histogram_tooltip') }}
                        </v-tooltip>

                    </v-card-title>
                    <v-card-text>
                        <div v-if="histogramChartData" style="position: relative">
                            <v-checkbox v-model="histogramLogScale" :label="$t('log')" style="position: absolute; bottom: 0; left: 1rem; z-index: 100" />
                            <ve-histogram

                                    :data="histogramChartData"
                                    :xAxis="{type: 'category', axisLabel: { rotate: 90 }, data: histogramChartXAxisData}"
                                    :yAxis="{type: histogramLogScale ? 'log' : 'value', min: histogramLogScale ? 0.1 : 0}"
                                    :settings="{labelMap: {'count': this.$t('title_count') }}"
                            >
                            </ve-histogram>
                        </div>
                        <LargeSpinner v-else />

                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
        <v-row class="align-stretch">

            <v-col cols="auto">
                <v-card height="100%">
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
                    md_="6"
                    lg_="4"
                    v-for="record in this.interestGroupTitlesSorted"
                    :key="record.interestGroup.short_name"
            >
                <v-card min-height="320px" height="100%" class="text-center">
                    <v-card-title v-text="record.interestGroup.name"></v-card-title>
                    <v-card-subtitle class="text-left">{{ $t('titles_with_most_interest') }}</v-card-subtitle>
                    <v-card-text>
                        <v-simple-table
                                v-if="record.titles && record.titles.length"
                                class="dashoard"
                                dense
                        >
                            <tbody>
                            <tr
                                    v-for="title in record.titles"
                                    :key="title.pk"
                            >
                                <td class="text-left">
                                    <router-link :to="{name: 'title-detail', params: {platformId: null, titleId: title.pk}}">
                                        {{ title.name }}
                                    </router-link>
                                </td>
                                <td class="text-right">{{ formatInteger(title.interests[record.interestGroup.short_name]) }}</td>
                            </tr>
                            </tbody>
                        </v-simple-table>
                        <div v-else-if="record.titles"> <!-- titles loaded, but no data -->
                            <div class="mt-8 mb-2"><v-icon large color="grey">fa-times</v-icon></div>
                            {{ $t('no_matching_titles') }}
                        </div>
                        <LargeSpinner v-else />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>

  import APIChart from '../components/APIChart'
  import {mapActions, mapGetters, mapState} from 'vuex'
  import axios from 'axios'
  import LargeSpinner from '../components/LargeSpinner'
  import { formatInteger} from '../libs/numbers'
  import { smartFormatFloat } from '../libs/numbers'
  import VeHistogram from 'v-charts/lib/histogram.common'

  export default {
    name: "DashboardPage",

    components: {
      LargeSpinner,
      APIChart,
      VeHistogram,
    },

    data () {
      return {
        interestReportType: null,
        interestGroupToTopTitles: {},
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
      }),
      interestGroupTitlesSorted () {
        let igs = this.interestGroups.filter(item => item.short_name !== 'other')
        if (igs) {
          let result = []
          for (let ig of igs.sort((a, b) => (a.important === b.important) ? a.name > b.name : a.important < b.important)) {
            if (ig.short_name in this.interestGroupToTopTitles) {
              result.push(this.interestGroupToTopTitles[ig.short_name])
            } else {
              result.push({interestGroup: ig, titles: null})
            }
          }
          return result
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
      }
    },

    methods: {
      ...mapActions({
        fetchInterestReportType: 'fetchInterestReportType',
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      smartFormatFloat: smartFormatFloat,
      async fetchReportTypes() {
        this.interestReportType = await this.fetchInterestReportType()
      },
      async fetchTitlesTopInterest() {
        this.interestGroupToTopTitles = {}
        for (let ig of this.interestGroups) {
          if (ig) {
            this.fetchTitleInterest(ig)
          }
        }
      },
      async fetchTitleInterest(interestGroup) {
        let url = this.titleInterestBaseUrl
        if (url) {
          url += `&order_by=${interestGroup.short_name}`
          try {
            let response = await axios.get(url)
            this.$set(this.interestGroupToTopTitles, interestGroup.short_name, {
              interestGroup: interestGroup,
              titles: response.data.results.filter(item => item.interests[interestGroup.short_name] > 0),
            })
          } catch (error) {
            this.showSnackbar({
              content: 'Error loading interesting titles: ' + error,
              color: 'error'
            })
          }
        }
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
      }
    },

    mounted () {
      this.fetchReportTypes()
      this.fetchTitlesTopInterest()
      this.fetchTotalInterest()
      this.fetchHistogramData()
    },

    watch: {
      interestGroups () {
        this.fetchTitlesTopInterest()
      },
      titleInterestBaseUrl () {
        this.fetchTitlesTopInterest()
      },
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

</style>
