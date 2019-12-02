<i18n lang="yaml" src="../locales/charts.yaml"></i18n>
<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
    standard_views: Standard views
    customizable_views: Customizable views
    mark_my_org: Highlight my organization

cs:
    standard_views: Standardní pohledy
    customizable_views: Nastavitelné pohledy
    mark_my_org: Zvýrazni mou organizaci
</i18n>

<template>
    <div v-if="loading" class="pt-2">
        <v-progress-linear
                indeterminate
                color="secondary"
        ></v-progress-linear>
    </div>
    <v-container fluid v-else class="pb-0">
        <v-row>
            <v-select
                    :items="reportViewsForSelect"
                    item-text="name"
                    v-model="selectedReportView"
                    :label="$t('available_report_types')"
                    :return-object="true"
            >
                <template v-slot:item="{item}">
                    <v-list-item-content>
                        <v-list-item-title v-html="item.name"></v-list-item-title>
                        <v-list-item-subtitle v-if="item.desc" v-html="item.desc"></v-list-item-subtitle>
                    </v-list-item-content>
                </template>
            </v-select>
        </v-row>

        <v-row class="mt-3 mb-3">
            <v-col>
            <ChartTypeSelector
                    :report-type="selectedReportView"
                    :scope="scope"
                    v-model="selectedChartType"/>
            </v-col>
            <v-col cols="auto" v-if="primaryDimension === 'organization' && this.organizationSelected">
                <v-switch v-model="showMarkLine" :label="$t('mark_my_org')"></v-switch>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
        <APIChart
                v-if="selectedReportView && selectedChartType"
                :type="typeOfChart"
                :report-type-id="selectedReportView.pk"
                :primary-dimension="primaryDimension"
                :secondary-dimension="secondaryDimension"
                :organization="organizationForChart"
                :platform="platformForChart"
                :title="titleId"
                :import-batch="importBatchId"
                :stack="this.selectedChartType.stack === undefined ? this.selectedChartType.chart_type === 'h-bar' : this.selectedChartType.stack"
                :order-by="this.selectedChartType.ordering"
                :ignore-date-range="!!importBatchId"
                :show-mark-line="showMarkLine"
        >
        </APIChart>
        <v-alert v-else-if="selectedReportView" type="warning" border="right" colored-border elevation="2">
            {{ $t('no_chart_types_available') }}
        </v-alert>
        <v-alert v-else type="warning" border="right" colored-border elevation="2">
            {{ $t('no_reports_available_for_title') }}
        </v-alert>
            </v-col>
        </v-row>
    </v-container>
</template>
<script>
  import APIChart from './APIChart'
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'
  import ChartTypeSelector from './ChartTypeSelector'

  export default {
    name: 'CounterChartSet',
    components: {APIChart, ChartTypeSelector},
    props: {
      platformId: {},
      titleId: {},
      reportViewsUrl: {},
      importBatchId: {},
      ignoreOrganization: {type: Boolean, default: false},
      scope: {default: '', required: false},
    },
    data () {
      return {
        reportViews: [],
        selectedReportView: null,
        selectedChartType: null,
        loading: false,
        showMarkLine: true,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStartText: 'dateRangeStartText',
        dateRangeEndText: 'dateRangeEndText',
        organizationSelected: 'organizationSelected',
      }),
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
        lang: 'appLanguage',
      }),
      organizationForChart () {
        /* which organization should be reported to the APIChart component
        * - in case we want to compare organizations, we should not add organization to
        * the filter */
        if (this.ignoreOrganization) {
          return null
        }
        if (this.selectedChartType && this.selectedChartType.ignore_organization) {
          return null
        }
        if (this.selectedOrganizationId === -1) {
          return null  // we want data for all organizations
        }
        return this.selectedOrganizationId
      },
      platformForChart () {
        if (this.selectedChartType && this.selectedChartType.ignore_platform) {
          return null
        }
        return this.platformId
      },
      reportViewsForSelect () {
        let out = []
        let standard = this.reportViews.filter(item => item.is_standard_view)
        let other = this.reportViews.filter(item => !item.is_standard_view)
        if (standard.length) {
          out.push({'header': this.$t('standard_views'), backgroundColor: 'blue'})
          out = out.concat(standard)
        }
        if (other.length) {
          if (out.length) {
            out.push({'divider': true})  // add divider between standard and custom
          }
          out.push({'header': this.$t('customizable_views')})
          out = out.concat(other)
        }
        return out
      },
      primaryDimension () {
        if (this.selectedChartType) {
          if (this.selectedChartType.primary_implicit_dimension) {
            return this.selectedChartType.primary_implicit_dimension
          } else if (this.selectedChartType.primary_dimension) {
            return this.selectedChartType.primary_dimension.short_name
          }
        }
        return null
      },
      secondaryDimension () {
        if (this.selectedChartType) {
          if (this.selectedChartType.secondary_implicit_dimension) {
            return this.selectedChartType.secondary_implicit_dimension
          } else if (this.selectedChartType.secondary_dimension) {
            return this.selectedChartType.secondary_dimension.short_name
          }
        }
        return null
      },
      typeOfChart () {
        if (this.selectedChartType) {
          if (this.selectedChartType.chart_type === 'v-bar')
            return 'histogram'
          else if (this.selectedChartType.chart_type === 'h-bar')
            return 'bar'
          else
            return 'line'
        }
        return null
      }

    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadReportViews () {
        this.reportViews = []
        let url = this.reportViewsUrl
        if (url) {
          this.loading = true
          try {
            const response = await axios.get(url)
            this.reportViews = response.data
            if (this.reportViewsForSelect.length > 1) {
              // if there is something, [0] is header, [1] is actuall reportView
              this.selectedReportView = this.reportViewsForSelect[1]
            }
          } catch (error) {
            console.log("ERROR: ", error)
            this.showSnackbar({content: 'Error loading title: ' + error})
          } finally {
            this.loading = false
          }
        }
      },
    },
    mounted () {
      this.loadReportViews()
    },
    watch: {
      reportViewsUrl () {
        this.loadReportViews()
      },

    }

  }
</script>

<style lang="scss">

    .v-select-list {
        .v-subheader {
            background-color: #ededed;
        }
    }

</style>
