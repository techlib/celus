<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <v-layout>
            <v-flex>
                <v-breadcrumbs :items="breadcrumbs" class="pl-0">
                    <template v-slot:item="props">
                        <router-link
                                v-if="props.item.linkName"
                                :to="{name: props.item.linkName, params: props.item.linkParams}"
                        >
                            {{ props.item.text }}
                        </router-link>
                        <span v-else>
                {{ props.item.text }}
            </span>
                    </template>
                </v-breadcrumbs>

                <h2 class="mb-4">{{ titleName }}</h2>

                <table class="overview mb-4 elevation-2">
                    <tr v-if="this.platformId">
                        <th>{{ $t('platform') }}</th>
                        <td>{{ platformName }}</td>
                    </tr>
                    <tr>
                        <th>{{ $t('title') }}</th>
                        <td>{{ titleName }}</td>
                    </tr>
                    <template v-if="title">
                        <tr v-for="(prop, index) in ['isbn', 'issn', 'eissn']" :key="index">
                            <th>{{ $t('title_fields.'+prop) }}</th>
                            <td>{{ title[prop] }}</td>
                        </tr>
                    </template>
                </table>
            </v-flex>
            <v-flex shrink v-if="coverImg">
                <img :src="coverImg" class="cover-image"/>
            </v-flex>
        </v-layout>

        <section v-if="isReady">
            <h3>{{ $t('overview') }}</h3>

            <div>
                <v-select
                        :items="reportTypes"
                        item-text="name"
                        item-value="short_name"
                        v-model="selectedReportType"
                        :label="$t('available_report_types')"
                >
                </v-select>
            </div>

            <div class="mt-3 mb-3">
                <v-btn-toggle v-model="chartTypeIndex" mandatory>
                    <v-btn v-for="(chartType, index) in chartTypes " flat :value="index" :key="index">
                        {{ chartType.name }}
                    </v-btn>
                </v-btn-toggle>
            </div>

            <APIChart
                    v-if="selectedReportType"
                    :report-type-name="selectedReportType"
                    :primary-dimension="selectedChartType.primary"
                    :secondary-dimension="selectedChartType.secondary ? selectedChartType.secondary : null"
                    :organization="selectedOrganization.pk"
                    :platform="platformId"
                    :title="titleId"
            >
            </APIChart>
            <div v-else>
                {{ $t('no_reports_available_for_title') }}
            </div>
        </section>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import APIChart from '../components/APIChart'
  import axios from 'axios'

  export default {
    name: 'TitleDetailPage',
    components: {
      APIChart,
    },
    props: {
      'platformId': {required: false, type: Number},
      'titleId': {required: true, type: Number},
    },
    data () {
      return {
        title: null,
        platformData: null,
        chartTypeIndex: 0,
        coverImg: null,
        reportTypes: [], // report types available for this title
        selectedReportType: null,
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      }),
      chartTypes () {
        let base = [
          {name: this.$i18n.t('chart.date_metric'), primary: 'date', secondary: 'metric'},
          {name: this.$i18n.t('chart.metric'), primary: 'metric'},
        ]
        let extra = [
          {name: this.$i18n.t('chart.accesstype'), primary: 'Access_Type'},
          {name: this.$i18n.t('chart.accessmethod'), primary: 'Access_Method'},
          {name: this.$i18n.t('chart.datatype'), primary: 'Data_Type'},
          {name: this.$i18n.t('chart.sectiontype'), primary: 'Section_Type'},
          {name: this.$i18n.t('chart.yop'), primary: 'YOP'},
        ]
        let reportType = this.selectedReportTypeObject
        if (reportType) {
          let dimNames = reportType.dimensions_sorted.map(dim => dim.short_name)
          for (let option of extra) {
            if (dimNames.indexOf(option.primary) >= 0) {
              base.push(option)
            }
          }
        }
        // if platform is not specified for the title, then we can show the split by platform
        if (this.platformId === null) {
          base.push({name: this.$i18n.t('chart.platform'), primary: 'platform'})
        }
        return base
      },
      selectedReportTypeObject () {
        for (let rt of this.reportTypes) {
          if (rt.short_name === this.selectedReportType)
            return rt
        }
        return null
      },
      selectedChartType () {
        return this.chartTypes[this.chartTypeIndex]
      },
      isReady () {
        return this.selectedOrganization && this.titleId
      },
      platform () {
        return this.platformData
      },
      platformName () {
        if (this.platform) {
          return this.platform.name
        }
        return ''
      },
      titleName () {
        if (this.title) {
          return this.title.name
        }
        return ''
      },
      breadcrumbs () {
        if (this.platformId) {
          return [
            {
              text: this.platformName,
              linkName: 'platform-detail',
              linkParams: {
                platformId: this.platformId
              }
            },
            {
              text: this.titleName,
            },
          ]
        }
        return [{text: this.titleName}]
      },
      titleUrl () {
        if (this.selectedOrganization && this.titleId) {
          if (this.platformId) {
            return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}`
          } else {
            // this is the case when no platform is specified
            return `/api/organization/${this.selectedOrganization.pk}/title/${this.titleId}`
          }
        }
        return null
      },
      reportTypesUrl () {
        if (this.selectedOrganization && this.titleId) {
          if (this.platformId) {
            return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/title/${this.titleId}/reports`
          } else {
            // this is the case when no platform is specified
            return `/api/organization/${this.selectedOrganization.pk}/title/${this.titleId}/reports`
          }
        }
        return null
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadTitle () {
        let url = this.titleUrl
        if (url) {
          try {
            const response = await axios.get(url)
            this.title = response.data
            this.getCoverImg()
          } catch (error) {
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      loadPlatform () {
        if (this.selectedOrganization) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`)
            .then(response => {
              this.platformData = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: ' + error})
            })
        }
      },
      async loadReportTypes () {
        let url = this.reportTypesUrl
        if (url) {
          try {
            const response = await axios.get(url)
            this.reportTypes = response.data
            if (this.reportTypes.length > 0) {
              this.selectedReportType = this.reportTypes[0].short_name
            } else {
              this.selectedReportType = null
            }
          } catch (error) {
            this.showSnackbar({content: 'Error loading title: ' + error})
          }
        }
      },
      getCoverImg () {
        if (this.title.isbn) {
          let isbn = this.title.isbn.replace(/-/g, '')
          axios.get(`https://www.googleapis.com/books/v1/volumes?q=isbn:${isbn}`)
            .then(response => {
              let items = response.data.items
              if (items.length > 0) {
                let item = items[0]
                this.coverImg = item.volumeInfo.imageLinks.thumbnail
              }
            })
            .catch(error => {
              console.info('Could not load cover image: ' + error)
            })
        }
      },
    },
    mounted () {
      if (this.platformId) {
        this.loadPlatform()
      }
      this.loadTitle()
      this.loadReportTypes()
    },
    watch: {
      selectedOrganization () {
        if (this.platformId) {
          this.loadPlatform()
        }
        this.loadTitle()
        this.loadReportTypes()
      },
    }
  }
</script>

<style scoped lang="scss">

    .thin {
        font-weight: 300;
    }

    table.overview {

        padding: 1rem;

        th {
            text-align: left;
            padding-right: 1.5rem;
        }
    }

    img.cover-image {
        max-width: 300px;
    }

</style>
