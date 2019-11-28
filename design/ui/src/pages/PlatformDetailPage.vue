<i18n lang="yaml" src="../locales/charts.yaml"></i18n>
<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
    no_info: Unfortunately there are no data about titles available for this platform.

cs:
    no_info: Pro tuto platformu bohužel nejsou dostupná žádná data o titulech.
</i18n>

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

                <h2 class="mb-4">{{ platform ? platform.name : '' }}</h2>

                <v-layout row ma-2 mb-4>
                    <v-flex shrink mr-sm-4>
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
                    </v-flex>
                    <v-flex shrink mr-sm-4>
                        <table v-if="platform" class="overview mb-4 elevation-2">
                            <tr>
                                <th>{{ $t('labels.title_count') }}</th>
                                <td class="text-right">
                                    <span v-if="platform.title_count === 'loading'" class="fas fa-spinner fa-spin subdued"></span>
                                    <span v-else>
                                        {{ formatInteger(platform.title_count) }}
                                    </span>
                                </td>
                            </tr>
                            <tr class="header">
                                <th colspan="2" v-text="$t('interest')"></th>
                            </tr>
                            <tr v-for="ig in interestGroups">
                                <th v-text="ig.name"></th>
                                <td class="text-right">
                                    <span v-if="platform.interests.loading" class="fas fa-spinner fa-spin subdued"></span>
                                    <span v-else>
                                        {{ formatInteger(platform.interests[ig.short_name]) }}
                                    </span>
                                </td>
                            </tr>
                        </table>
                    </v-flex>
                    <v-spacer></v-spacer>
                    <v-flex shrink v-if="showAdminStuff && organizationSelected">
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
                    </v-flex>
                </v-layout>
            </v-flex>

        </v-layout>

        <section class="mb-5">
            <AnnotationsWidget v-if="platform" :platform="platform" :allow-add="showAdminStuff" ref="annotWidget"></AnnotationsWidget>
        </section>

        <section v-if="selectedOrganizationId && platform">
            <v-layout>
                <v-flex><h3>{{ $t('overview') }}</h3></v-flex>
                <v-flex shrink>
                    <data-export-widget :platform="platformId"></data-export-widget>
                </v-flex>
            </v-layout>
            <CounterChartSet
                    :platform-id="platformId"
                    :title-id="null"
                    :report-views-url="reportViewsUrl"
            >
            </CounterChartSet>
        </section>

        <section v-if="platform && platform.title_count">
            <h3 class="pt-3">{{ $t('titles') }}</h3>

            <InterestGroupSelector />
            <TitleList :url="titleListURL" :platform-id="platformId"></TitleList>
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

  export default {
    name: 'PlatformDetailPage',
    components: {
      DataExportWidget,
      TitleList,
      CounterChartSet,
      AnnotationsWidget,
      AddAnnotationButton,
      InterestGroupSelector,
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
            this.loadPlatformDetails()
          } catch(error) {
              this.showSnackbar({content: 'Error loading platforms: '+error})
          }
        }
      },
      async loadPlatformDetails () {
        if (this.selectedOrganizationId) {
          this.$set(this.platform, 'interests', {loading: true})
          this.$set(this.platform, 'title_count', 'loading')
          try {
            let response = await axios.get(this.platformInterestUrl)
            this.$set(this.platform, 'interests', response.data)
            this.$set(this.platform, 'title_count', response.data.title_count)
          } catch(error) {
            this.showSnackbar({content: 'Error loading platforms: '+error, color: 'error'})
            this.$set(this.platform, 'interests', {loading: false})
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
        this.loadPlatformDetails()
      }
    }
  }
</script>

<style scoped lang="scss">

    .thin {
        font-weight: 300;
    }


    table.overview {

        padding: 1rem;

        tr.header {
            th {
                font-variant: small-caps;
                font-weight: 300;
                font-size: 82.5%;
                border-bottom: solid 1px #dddddd;
                padding-top: 0.5rem;
            }
        }

        th {
            text-align: left;
            padding-right: 1.5rem;
        }
    }

</style>
