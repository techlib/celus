<i18n>
en:
    platform: Platform
    titles: Titles
cs:
    platform: Platforma
    titles: Tituly
</i18n>

<template>
    <div>
        <h2 class="mb-4"><span class="thin">{{ $t('platform') }}</span> {{ platform ? platform.name : '' }}</h2>

        <APIChart
                primary-dimension="date"
                report-type-name="TR"
                secondary-dimension="metric"
            >
        </APIChart>

        <h3 class="pt-3">{{ $t('titles') }}</h3>
        <TitleList :url="titleListURL"></TitleList>
    </div>

</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import TitleList from '../components/TitleList'
  import APIChart from '../components/APIChart'
  import axios from 'axios'

  export default {
    name: 'PlatformDetailPage',
    components: {
      APIChart,
      TitleList,
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
      }),
      titleListURL () {
        if (this.platform !== null) {
          return `/api/organization/${this.selectedOrganization.pk}/platform/${this.platform.pk}/title/`
        }
        return null
      }
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

<style scoped type="scss">

    .thin {
        font-weight: 300;
    }

</style>
