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
                        <tr v-for="(prop, index) in ['isbn', 'issn', 'eissn', 'doi']" :key="index">
                            <th>{{ $t('title_fields.'+prop) }}</th>
                            <td>{{ title[prop] }}</td>
                        </tr>
                    </template>
                </table>
            </v-flex>
            <v-flex shrink>
                <img  v-if="coverImg" :alt="$t('cover-image')" :src="coverImg" class="cover-image"/>
            </v-flex>
        </v-layout>

        <section v-if="isReady">
            <v-layout>
                <v-flex>
                    <h3>{{ $t('overview') }}</h3>
                </v-flex>
                <v-flex shrink>
                <data-export-widget
                        :title="titleId"
                        :platform="platformId"
                >
                </data-export-widget>
                    
                </v-flex>
            </v-layout>

            <CounterChartSet
                    :chart-extend="chartExtend"
                    :platform-id="platformId"
                    :title-id="titleId"
                    :report-types-url="reportTypesUrl"
                    :extra-chart-types="extraChartTypes"
            >
            </CounterChartSet>
        </section>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import axios from 'axios'
  import CounterChartSet from '../components/CounterChartSet'
  import DataExportWidget from '../components/DataExportWidget'

  export default {
    name: 'TitleDetailPage',
    components: {
      DataExportWidget,
      CounterChartSet,

    },
    props: {
      'platformId': {required: false, type: Number},
      'titleId': {required: true, type: Number},
    },
    data () {
      return {
        title: null,
        platformData: null,
        coverImg: null,
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      }),
      extraChartTypes () {
        let base = []
        // if platform is not specified for the title, then we can show the split by platform
        if (this.platformId === null) {
          base.push({name: this.$i18n.t('chart.platform'), primary: 'platform'})
        }
        return base
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
              text: this.$t('pages.platforms'),
              linkName: 'platform-list',
            },
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
        return [
          {
              text: this.$t('titles'),
              linkName: 'title-list',
          },
          {
            text: this.titleName
          },
        ]
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
      chartExtend () {
        return {}
        /* return {
          series (item) {
            item[0].data = item[0].data.map((v, index) => ({
              value: v,
              itemStyle: { color: '#f00' }
            }))
            return item
          }
        } */
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
    },
    watch: {
      selectedOrganization () {
        if (this.platformId) {
          this.loadPlatform()
        }
        this.loadTitle()
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
