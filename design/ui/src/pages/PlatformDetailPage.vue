<i18n lang="yaml" src="../locales/charts.yaml"></i18n>
<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
    no_info: Unfortunately there are no data about titles available for this platform.

cs:
    no_info: Pro tuto platformu bohužel nejsou dostupná žádná data o titulech.
</i18n>

<template>
    <div class="px-md-2">
        <div>
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
        </div>

        <h2 class="mb-0">{{ platform ? platform.name : '' }}</h2>

        <v-container fluid class="px-0">
            <v-row>
                <v-col cols="auto" mr-sm-4>
                    <table v-if="platform" class="overview mb-4 elevation-2">
                        <tr>
                            <th>{{ $t('labels.provider') }}</th>
                            <td>{{ platform.provider }}</td>
                        </tr>
                        <tr>
                            <th>{{ $t('labels.url') }}</th>
                            <td><a :href="platform.url">{{ platform.url }}</a></td>
                        </tr>
                    </table>
                </v-col>
                <v-col cols="auto" mr-sm-4>
                    <table v-if="platform" class="overview mb-4 elevation-2">
                        <tr>
                            <th>{{ $t('labels.title_count') }}</th>
                            <td class="text-right">
                                <span
                                        v-if="platform.title_count === 'loading'"
                                        class="fas fa-spinner fa-spin subdued">
                                </span>
                                <span v-else>
                                    {{ formatInteger(platform.title_count) }}
                                </span>
                            </td>
                        </tr>
                        <tr class="header">
                            <th colspan="2" v-text="$t('interest')"></th>
                        </tr>
                        <tr v-for="ig in interestGroups" :key="ig.pk">
                            <th
                                    v-text="ig.name"
                                    :class="{'subdued-th': platform.interests.loading || platform.interests[ig.short_name] === 0}">
                            </th>
                            <td class="text-right">
                                <span
                                        v-if="platform.interests.loading"
                                        class="fas fa-spinner fa-spin subdued">
                                </span>
                                <span v-else :class="{'subdued': platform.interests[ig.short_name] === 0}">
                                    {{ formatInteger(platform.interests[ig.short_name]) }}
                                </span>
                            </td>
                        </tr>
                    </table>
                </v-col>
                <v-spacer></v-spacer>
                <v-col cols="auto" v-if="showAdminStuff && organizationSelected">
                    <v-card>
                        <!--v-card-title>
                            {{ $t('title_fields.actions') }}
                        </v-card-title-->
                        <v-card-text>
                            <div>
                                <v-btn
                                        text small
                                        :to="{name: 'platform-upload-data', params: {platformId: platformId}}"
                                >
                                    <v-icon small class="mr-2">fa-upload</v-icon>
                                    {{ $t('actions.upload_custom_data') }}
                                </v-btn>

                            </div>
                            <div>
                                <AddAnnotationButton
                                        :platform="platform"
                                        @update="refreshAnnotations()"
                                        text
                                        small
                                />
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </v-container>

        <section class="mb-5" v-if="platform">
            <AnnotationsWidget :platform="platform" :allow-add="showAdminStuff" ref="annotWidget"></AnnotationsWidget>
        </section>

        <section v-if="selectedOrganizationId && platform">
            <v-container fluid class="pa-0">
                <v-row class="ma-0">
                    <v-col class="py-0"><h3>{{ $t('overview') }}</h3></v-col>
                    <v-col cols="auto" class="py-0">
                        <raw-data-export-widget :platform="platformId"></raw-data-export-widget>
                        <!--data-export-widget :platform="platformId"></data-export-widget-->
                    </v-col>
                </v-row>
            </v-container>
            <CounterChartSet
                    :platform-id="platformId"
                    :title-id="null"
                    :report-views-url="reportViewsUrl"
                    scope="platform"
            >
            </CounterChartSet>
        </section>

        <section v-if="platform && platform.title_count">
            <h3 class="pt-3">{{ $t('titles') }}</h3>

            <InterestGroupSelector />
            <TitleList :url="titleListURL" :platform-id="platformId" :order-interest="orderInterest"></TitleList>
        </section>
        <section v-if="platform && !platform.title_count">
            <v-container fluid>
                <v-alert elevation="2" colored-border border="right" type="warning">{{ $t('no_info') }}</v-alert>
            </v-container>
        </section>
    </div>

</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import TitleList from '../components/TitleList'
  import axios from 'axios'
  import CounterChartSet from '../components/CounterChartSet'
  import DataExportWidget from '../components/DataExportWidget'
  import {formatInteger} from '../libs/numbers'
  import AnnotationsWidget from '../components/AnnotationsWidget'
  import AddAnnotationButton from '../components/AddAnnotationButton'
  import InterestGroupSelector from '../components/InterestGroupSelector'
  import RawDataExportWidget from '../components/RawDataExportWidget'

  export default {
    name: 'PlatformDetailPage',
    components: {
      DataExportWidget,
      TitleList,
      CounterChartSet,
      AnnotationsWidget,
      AddAnnotationButton,
      InterestGroupSelector,
      RawDataExportWidget,
    },
    props: {
      'platformId': {required: true},
    },
    data () {
      return {
        platform: null,
      }
    },
    computed: {
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        showAdminStuff: 'showAdminStuff',
        organizationSelected: 'organizationSelected',
        activeInterestGroups: 'selectedGroupObjects',
      }),
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
        interestGroups: state => state.interest.interestGroups,
      }),
      titleListURL () {
        if (this.platform !== null) {
          return `/api/organization/${this.selectedOrganizationId}/platform/${this.platform.pk}/title-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      reportViewsUrl () {
        if (this.selectedOrganizationId && this.platformId) {
            return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/report-views/`
        }
        return null
      },
      platformInterestUrl () {
        if (this.selectedOrganizationId) {
          return `/api/organization/${this.selectedOrganizationId}/platform-interest/${this.platformId}/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      platformTitleCountUrl () {
        if (this.selectedOrganizationId) {
          return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      breadcrumbs () {
          return [
            {
              text: this.$t('pages.platforms'),
              linkName: 'platform-list',
            },
            {
              text: this.platform === null ? '' : this.platform.name,
            }
        ]
      },
      orderInterest () {
        // The interest that should be used for sorting the titles
        if (this.activeInterestGroups.length) {
          return this.activeInterestGroups[0].short_name
        }
        return null
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      formatInteger: formatInteger,
      async loadPlatform () {
        if (this.selectedOrganizationId) {
          try {
            let response = await axios.get(`/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/`)
            this.platform = response.data
            this.loadPlatformTitleCount()
            this.loadPlatformInterest()
          } catch(error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
      async loadPlatformInterest () {
        if (this.platformInterestUrl) {
          this.$set(this.platform, 'interests', {loading: true})
          try {
            let response = await axios.get(this.platformInterestUrl)
            this.$set(this.platform, 'interests', response.data)
          } catch(error) {
            this.showSnackbar({content: 'Error loading interest: '+error, color: 'error'})
            this.$set(this.platform, 'interests', {loading: false})
          }
        }
      },
      async loadPlatformTitleCount () {
        if (this.platformTitleCountUrl) {
          this.$set(this.platform, 'title_count', 'loading')
          try {
            let response = await axios.get(this.platformTitleCountUrl)
            this.$set(this.platform, 'title_count', response.data.title_count)
          } catch(error) {
            this.showSnackbar({content: 'Error loading title count: '+error, color: 'error'})
            this.$set(this.platform, 'title_count', null)
          }
        }
      },
      refreshAnnotations () {
        this.$refs.annotWidget.fetchAnnotations()
      }
    },
    created () {
      this.loadPlatform()
    },
    watch: {
      selectedOrganizationId () {
        this.loadPlatform()
      },
      platformInterestUrl () {
        this.loadPlatformInterest()
      },
      platformTitleCountUrl () {
        this.loadPlatformTitleCount()
      }
    }
  }
</script>

<style lang="scss">

    .thin {
        font-weight: 300;
    }


    table.overview {
        padding: 1rem;

        tr.header {
            th {
                font-variant: small-caps;
                font-weight: 500;
                font-size: 82.5%;
                border-bottom: solid 1px #dddddd;
                padding-top: 0.5rem;
            }
            &:first-child {
                th {
                    padding-top: 0;
                }
            }
        }

        th {
            text-align: left;
            padding-right: 1.5rem;
            font-weight: 300;

            &.subdued-th {
                //font-weight: normal;
                color: #999999;
            }
        }
    }

</style>
