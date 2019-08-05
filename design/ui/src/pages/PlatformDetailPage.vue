<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <h2 class="mb-4"><span class="thin">{{ $t('platform') }}:</span> {{ platform ? platform.name : '' }}</h2>

        <section v-if="selectedOrganization && platform">
            <h3>{{ $t('overview') }}</h3>

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
  import { mapActions, mapGetters } from 'vuex'
  import TitleList from '../components/TitleList'
  import axios from 'axios'
  import CounterChartSet from './CounterChartSet'

  export default {
    name: 'PlatformDetailPage',
    components: {
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
        selectedOrganization: 'selectedOrganization',
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
      }),
      titleListURL () {
        if (this.platform !== null) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platform.pk}/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
        }
        return null
      },
      reportTypesUrl () {
        if (this.selectedOrganization && this.platformId) {
            return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/reports`
        }
        return null
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadPlatform () {
        if (this.selectedOrganization) {
          axios.get(`/api/organization/${this.selectedOrganization.pk}/platform/${this.platformId}/`)
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
      selectedOrganization () {
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
