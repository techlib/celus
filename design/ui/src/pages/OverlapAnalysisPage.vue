<i18n lang="yaml">
en:
  multiplatform_titles: Titles available from more than one platform
  no_overlap_titles: There are no titles available from more than one platform

cs:
  multiplatform_titles: Tituly dostupné na více než jedné platformě
  no_overlap_titles: Nebyly nalezeny žádné tituly dostupné na více platformách
</i18n>

<template>
  <div>
    <section v-if="selectedOrganizationId">
      <h3 class="pt-3">{{ $t("multiplatform_titles") }}</h3>

      <TitleList
        :url="titleListURL"
        :interest-by-platform="true"
        :no-data-text="$t('no_overlap_titles')"
      ></TitleList>
    </section>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import TitleList from "@/components/TitleList";
import InterestGroupSelector from "@/components/selectors/InterestGroupSelector";

export default {
  name: "OverlapAnalysisPage",
  components: {
    TitleList,
    InterestGroupSelector,
  },
  props: {},
  data() {
    return {};
  },
  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    titleListURL() {
      return `/api/organization/${this.selectedOrganizationId}/title-interest-by-platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&multiplatform`;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
  },
};
</script>

<style scoped lang="scss">
.thin {
  font-weight: 300;
}
</style>
