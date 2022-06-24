<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  validity: Validity
  valid: Valid
  future: Valid in the future
  outdated: Outdated

cs:
  validity: Platnost
  valid: Platné
  future: Platné v budoucnu
  outdated: Prošlé
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0">
        <h2>{{ $t("labels.annotations") }}</h2>
      </v-col>
      <v-spacer></v-spacer>
      <v-col class="pb-0" cols="auto" v-if="showAdminStuff">
        <AddAnnotationButton @update="fetchAnnotations" />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-text>
            <v-container fluid class="pt-0 px-0 px-sm-2">
              <v-row>
                <v-spacer></v-spacer>
                <v-col cols="4">
                  <v-text-field
                    v-model="searchDebounced"
                    append-icon="fa-search"
                    :label="$t('labels.search')"
                    single-line
                    hide-details
                  >
                  </v-text-field>
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="4">
                  <v-select
                    v-model="filterOrganization"
                    :items="Object.values(organizations)"
                    :label="$t('organization')"
                    item-value="pk"
                    item-text="name"
                    clearable
                    clear-icon="fas fa-times"
                    @change="() => (page = 1)"
                  ></v-select>
                </v-col>
                <v-col cols="6">
                  <v-select
                    v-model="filterPlatforms"
                    :label="$t('title_fields.platforms')"
                    :items="platforms"
                    item-value="pk"
                    item-text="name"
                    multiple
                    clearable
                    clear-icon="fas fa-times"
                    @change="() => (page = 1)"
                  ></v-select>
                </v-col>
                <v-col cols="2">
                  <v-select
                    v-model="filterValidity"
                    :items="validities"
                    :label="$t('validity')"
                    clearable
                    clear-icon="fas fa-times"
                    @change="() => (page = 1)"
                  ></v-select>
                </v-col>
              </v-row>
              <AnnotationList
                v-if="annotations"
                :loading="loading"
                :annotations="annotations.results"
                :platforms="platforms"
                :page="page"
                :server-items-length="annotations.count"
                @update:options="options = $event"
                @updated="fetchAnnotations"
              />
            </v-container>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState, mapGetters } from "vuex";
import debounce from "lodash/debounce";
import AddAnnotationButton from "@/components/AddAnnotationButton";
import AnnotationList from "@/components/AnnotationList";
import cancellation from "@/mixins/cancellation";

export default {
  name: "AnnotationListPage",

  mixins: [cancellation],

  components: {
    AnnotationList,
    AddAnnotationButton,
  },

  data() {
    return {
      loading: false,
      annotations: null,
      platforms: [],
      filterOrganization: null,
      filterPlatforms: null,
      filterValidity: null,
      validities: [
        { text: this.$t("valid"), value: "valid" },
        { text: this.$t("future"), value: "future" },
        { text: this.$t("outdated"), value: "outdated" },
      ],
      search: "",
      page: 1,
      itemsPerPage: undefined,
      ordering: undefined,
      count: 0,
      options: {},
    };
  },

  computed: {
    ...mapState({
      organizations: "organizations",
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      showAdminStuff: "showAdminStuff",
    }),
    basePlatformUrl() {
      return `/api/organization/${this.selectedOrganizationId}/platform/`;
    },
    params() {
      return {
        organization: this.filterOrganization,
        platform: this.filterPlatforms,
        page: this.page,
        page_size: this.page_size,
        ordering: this.ordering,
        ...(this.searchDebounced && { search: this.searchDebounced }),
        ...(this.filterValidity && { validity: this.filterValidity }),
      };
    },
    locale() {
      return this.$i18n.locale === "en" ? "en-GB" : this.$i18n.locale;
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
        this.page = 1;
      }, 500),
    },
  },
  methods: {
    async fetchAnnotations() {
      this.loading = true;
      const { response } = await this.http({
        url: "/api/annotations/",
        params: this.params,
        label: "annotations",
      });
      this.loading = false;
      if (response) this.annotations = response.data;
    },
    async fetchPlatforms() {
      if (!this.selectedOrganizationId) return;
      const { response } = await this.http({ url: this.basePlatformUrl });
      if (response) this.platforms = response.data;
    },
    filterUpdated() {
      this.page = 1;
      this.fetchAnnotations();
    },
  },
  mounted() {
    this.fetchAnnotations();
    this.fetchPlatforms();
  },
  watch: {
    options: {
      handler() {
        const { page, itemsPerPage, sortBy, sortDesc } = this.options;
        this.page = page;
        this.page_size = itemsPerPage;
        this.ordering = sortBy.map(
          (field, i) => (sortDesc[i] ? "-" : "") + field.replace(".", "__")
        );
      },
    },
    params: {
      handler() {
        this.fetchAnnotations();
      },
      deep: true,
    },
  },
};
</script>
