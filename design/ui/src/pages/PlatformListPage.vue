<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
    <v-container fluid>
        <v-row>
            <v-col>
                <h2>{{ $t('pages.platforms') }}</h2>
            </v-col>
            <v-spacer></v-spacer>
            <v-col v-if="showAdminStuff && organizationSelected" cols="auto">
                <ManualUploadButton />
                <AddAnnotationButton @update="refreshAnnotations()" class="ml-2"/>
            </v-col>
        </v-row>
        <v-row>
            <AnnotationsWidget :allow-add="showAdminStuff" ref="annotWidget"/>
        </v-row>
        <v-row>
            <v-col>
                <v-card>
                    <v-card-text>
                        <v-btn-toggle v-model="viewType" class="float-right">
                            <v-btn value="interest" small><v-icon small>fa fa-list</v-icon></v-btn>
                            <v-btn value="chart" small><v-icon small>fa fa-chart-bar</v-icon></v-btn>
                            <v-btn value="cost" small><v-icon small>fa fa-dollar-sign</v-icon></v-btn>
                        </v-btn-toggle>

                        <div v-if="viewType === 'chart'" class="pt-10">
                            <PlatformInterestChart :platforms="platforms">
                                <v-btn
                                        :href="platformInterestURL+'&format=csv'"
                                        color="secondary"
                                >
                                    <v-icon left small>fa-download</v-icon>
                                    Export
                                </v-btn>
                            </PlatformInterestChart>
                        </div>
                        <div v-else-if="viewType === 'cost'">
                            <InterestGroupSelector />
                            <PlatformCostList :loading="loading" :platforms="platforms" />
                        </div>
                        <div v-else>
                            <InterestGroupSelector />
                            <PlatformList :loading="loading" :platforms="platforms" />                                         </div>
                     </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'
  import { formatInteger } from '../libs/numbers'
  import { createEmptyInterestRecord, createLoadingInterestRecord, } from '../libs/interest'
  import AnnotationsWidget from '../components/AnnotationsWidget'
  import AddAnnotationButton from '../components/AddAnnotationButton'
  import InterestGroupSelector from '../components/InterestGroupSelector'
  import PlatformInterestChart from '../components/PlatformInterestChart'
  import PlatformCostList from '../components/PlatformCostList'
  import PlatformList from '../components/PlatformList'
  import ManualUploadButton from '../components/ManualUploadButton'

  export default {
    name: 'PlatformListPage',
    components: {
      PlatformList,
      PlatformCostList,
      ManualUploadButton,
      AnnotationsWidget,
      AddAnnotationButton,
      InterestGroupSelector,
      PlatformInterestChart,
    },
    data () {
      return {
        platforms: [],
        search: '',
        loading: false,
        showUploadDataDialog: false,
        annotations: {},
        viewType: 'interest'
      }
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        formatNumber: 'formatNumber',
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        showAdminStuff: 'showAdminStuff',
        organizationSelected: 'organizationSelected',
        activeInterestGroups: 'selectedGroupObjects',
      }),
      platformsURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      platformInterestURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      platformTitleCountURL () {
        return `/api/organization/${this.selectedOrganizationId}/platform/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
      annotationsUrl () {
        let url = `/api/annotations/?start_date=${this.dateRangeStart}&end_date=${this.dateRangeEnd}`
        if (this.organizationSelected) {
          url += `&organization=${this.selectedOrganizationId}`
        }
        return url
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      async loadPlatforms () {
        if (this.selectedOrganizationId) {
          this.loading = true
          try {
            let response = await axios.get(this.platformsURL)
            this.platforms = response.data.map(item => {item.interests = createLoadingInterestRecord(); item.title_count = 'loading'; return item})
            this.loadPlatformInterest()
            this.loadPlatformTitleCount()
            this.loadPlatformSushiCounts()
            this.loadAnnotations()
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error, color: 'error'})
          } finally {
            this.loading = false
          }
        }
      },
      async loadPlatformInterest () {
        try {
          let response = await axios.get(this.platformInterestURL)
          let pkToRow = {}
          for (let row of response.data) {
            pkToRow[row.platform] = row
          }
          for (let platform of this.platforms) {
            let newData = pkToRow[platform.pk]
            if (newData) {
              this.$set(platform, 'interests', newData)
            } else {
              platform.interests = createEmptyInterestRecord()
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading platform interest: '+error, color: 'warning'})
        }
      },
      async loadPlatformTitleCount () {
        try {
          let response = await axios.get(this.platformTitleCountURL)
          let pkToRow = {}
          for (let row of response.data) {
            pkToRow[row.platform] = row
          }
          for (let platform of this.platforms) {
            let newData = pkToRow[platform.pk]
            if (newData) {
              platform.title_count = newData.title_count
            } else {
              platform.title_count = null
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading platform title count: '+error, color: 'warning'})
        }
      },
      async loadPlatformSushiCounts () {
        if (this.selectedOrganizationId) {
          try {
            let response = await axios.get(`/api/organization/${this.selectedOrganizationId}/sushi-credentials-versions/`)
            for (let platform of this.platforms) {
              let key = platform.pk.toString()
              if (key in response.data) {
                this.$set(platform, 'sushi_credentials_versions', response.data[key])
              } else {
                this.$set(platform, 'sushi_credentials_versions', {})
              }
            }
          } catch (error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
      async loadAnnotations () {
        this.annotations = {}
        try {
          let response = await axios.get(this.annotationsUrl)
          this.annotations = {}
          // populate the this.annotations object
          for (let annot of response.data.filter(item => item.platform != null)) {
            if (!(annot.platform.pk in this.annotations)) {
              this.annotations[annot.platform.pk] = []
            }
            this.annotations[annot.platform.pk].push(annot)
          }
          // assign annotations to individual platform
          for (let platform of this.platforms) {
            if (platform.pk in this.annotations) {
              this.$set(platform, 'annotations', this.annotations[platform.pk])
            }
          }
        } catch (error) {
          this.showSnackbar({content: 'Error loading annotations: ' + error, color: 'error'})
        }
      },
      refreshAnnotations () {
        this.$refs.annotWidget.fetchAnnotations()
        this.loadAnnotations()
      },
    },
    created () {
      this.loadPlatforms()
    },
    watch: {
      selectedOrganizationId () {
        this.loadPlatforms()
      },
      dateRangeStart () {
        this.loadPlatforms()
      },
      dateRangeEnd () {
        this.loadPlatforms()
      }
    }
  }
</script>

<style lang="scss">
    table.v-table {
        thead {
            th.wrap {
                white-space: normal;
            }
        }
    }
</style>
