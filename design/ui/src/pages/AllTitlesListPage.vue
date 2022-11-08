<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <div>
    <section v-if="selectedOrganizationId">
      <h2 class="pt-3 pl-3">{{ $t("titles") }}</h2>

      <InterestGroupSelector />

      <TitleList :url="titleListURL"></TitleList>
    </section>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import TitleList from "@/components/TitleList";
import InterestGroupSelector from "@/components/selectors/InterestGroupSelector";

export default {
  name: "AllTitlesListPage",
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
      return `/api/organization/${this.selectedOrganizationId}/title-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
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
