<i18n src="../locales/charts.yaml"></i18n>
<i18n src="../locales/common.yaml"></i18n>

<template>
    <div>
        <section v-if="selectedOrganization">

            <h3 class="pt-3">{{ $t('titles') }}</h3>
            <TitleList :url="titleListURL"></TitleList>
        </section>
    </div>
</template>

<script>
  import { mapActions, mapGetters } from 'vuex'
  import TitleList from '../components/TitleList'

  export default {
    name: 'AllTitlesListPage',
    components: {
      TitleList,
    },
    props: {
    },
    data () {
      return {
      }
    },
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
      }),
      titleListURL () {
        return `/api/organization/${this.selectedOrganization.pk}/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`
      },
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
    },
  }
</script>

<style scoped lang="scss">

    .thin {
        font-weight: 300;
    }

</style>
