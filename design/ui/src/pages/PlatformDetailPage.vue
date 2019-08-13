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

                <h2 class="mb-4">{{ platform ? platform.name : '' }}</h2>

                <v-layout row>
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
                    <v-flex>
                        <table v-if="platform" class="overview mb-4 elevation-2">
                            <tr>
                                <th>{{ $t('labels.title_count') }}</th>
                                <td class="text-right">{{ platform.title_count ? platform.title_count : '-' }}</td>
                            </tr>
                            <tr>
                                <th>{{ $t('interests.title') }}</th>
                                <td class="text-right">{{ platform.interests.title.value ? platform.interests.title.value : '-' }}</td>
                            </tr>
                            <tr>
                                <th>{{ $t('interests.database') }}</th>
                                <td class="text-right">{{ platform.interests.database.value ? platform.interests.database.value : '-' }}</td>
                            </tr>
                        </table>
                    </v-flex>
                </v-layout>
            </v-flex>

        </v-layout>

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
                    :report-types-url="reportTypesUrl"
            >
            </CounterChartSet>
        </section>

        <h3 class="pt-3">{{ $t('titles') }}</h3>

        <TitleList :url="titleListURL" :platform-id="platformId"></TitleList>
    </div>

</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import TitleList from '../components/TitleList'
  import axios from 'axios'
  import CounterChartSet from '../components/CounterChartSet'
  import DataExportWidget from '../components/DataExportWidget'

  export default {
    name: 'PlatformDetailPage',
    components: {
      DataExportWidget,
      TitleList,
      CounterChartSet,
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
      }),
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      titleListURL () {
        if (this.platform !== null) {
          return `/api/organization/${this.selectedOrganizationId}/platform/${this.platform.pk}/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      reportTypesUrl () {
        if (this.selectedOrganizationId && this.platformId) {
            return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/reports`
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
      loadPlatform () {
        if (this.selectedOrganizationId) {
          axios.get(`/api/organization/${this.selectedOrganizationId}/detailed-platform/${this.platformId}/`)
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
      selectedOrganizationId () {
        this.loadPlatform()
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

        th {
            text-align: left;
            padding-right: 1.5rem;
        }
    }

</style>
