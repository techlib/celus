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
          axios.get(`/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/`)
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

</style>
