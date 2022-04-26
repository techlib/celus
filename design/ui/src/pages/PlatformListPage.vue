<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0">
        <h2>{{ $t("pages.platforms") }}</h2>
      </v-col>
      <v-spacer></v-spacer>
      <v-col
        v-if="showAdminStuff"
        cols="auto"
        class="d-none d-sm-block pb-0 pt-4"
      >
        <v-container fluid class="py-0">
          <v-row>
            <v-col
              v-if="allowUserCreatePlatforms"
              cols="auto"
              class="pa-1 pr-0"
            >
              <AddPlatformButton @update-platforms="loadPlatforms()" />
            </v-col>
            <v-col
              cols="auto"
              class="pa-1"
              v-if="allowManualDataUpload && organizationSelected"
            >
              <ManualUploadButton />
            </v-col>
            <v-col cols="auto" class="pa-1 pr-0">
              <AddAnnotationButton @update="refreshAnnotations()" />
            </v-col>
          </v-row>
        </v-container>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="py-0">
        <AnnotationsWidget
          :allow-add="showAdminStuff"
          ref="annotWidget"
          class="pt-4"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-text>
            <v-btn-toggle v-model="viewType" class="float-sm-right">
              <v-btn value="interest" small
                ><v-icon small>fa fa-list</v-icon></v-btn
              >
              <v-btn value="chart" small
                ><v-icon small>fa fa-chart-bar</v-icon></v-btn
              >
              <v-btn value="cost" small
                ><v-icon small>fa fa-dollar-sign</v-icon></v-btn
              >
            </v-btn-toggle>

            <div
              v-if="viewType === 'chart'"
              class="pt-10"
              style="min-height: 70vh"
            >
              <PlatformInterestChart :platforms="platforms">
                <v-btn
                  :href="platformInterestURL + '&format=csv'"
                  color="secondary"
                >
                  <v-icon left small>fas fa-file-export</v-icon>
                  Export
                </v-btn>
              </PlatformInterestChart>
            </div>
            <div v-else-if="viewType === 'cost'">
              <InterestGroupSelector />
              <PlatformCostList :loading="loading" :platforms="platforms" />
            </div>
            <div v-else>
              <InterestGroupSelector />
              <PlatformList
                :loading="loading"
                :platforms="platforms"
                @update-platforms="loadPlatforms()"
              />
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import { formatInteger } from "@/libs/numbers";
import {
  createEmptyInterestRecord,
  createLoadingInterestRecord,
} from "@/libs/interest";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import AddAnnotationButton from "@/components/AddAnnotationButton";
import AddPlatformButton from "@/components/AddPlatformButton";
import InterestGroupSelector from "@/components/InterestGroupSelector";
import PlatformInterestChart from "@/components/PlatformInterestChart";
import PlatformCostList from "@/components/PlatformCostList";
import PlatformList from "@/components/PlatformList";
import ManualUploadButton from "@/components/ManualUploadButton";
import cancellation from "@/mixins/cancellation";

export default {
  name: "PlatformListPage",

  mixins: [cancellation],

  components: {
    PlatformList,
    PlatformCostList,
    ManualUploadButton,
    AnnotationsWidget,
    AddAnnotationButton,
    AddPlatformButton,
    InterestGroupSelector,
    PlatformInterestChart,
  },
  data() {
    return {
      platforms: [],
      loading: false,
      showUploadDataDialog: false,
      annotations: {},
      viewType: "interest",
    };
  },
  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      formatNumber: "formatNumber",
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      showAdminStuff: "showAdminStuff",
      organizationSelected: "organizationSelected",
      allowManualDataUpload: "allowManualDataUpload",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    platformsURL() {
      return `/api/organization/${this.selectedOrganizationId}/platform/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&used_only`;
    },
    platformInterestURL() {
      return `/api/organization/${this.selectedOrganizationId}/platform-interest/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
    },
    platformTitleCountURL() {
      return `/api/organization/${this.selectedOrganizationId}/platform/title-count/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
    },
    annotationsUrl() {
      let url = `/api/annotations/?start_date=${this.dateRangeStart}&end_date=${this.dateRangeEnd}&no_page=1`;
      if (this.organizationSelected) {
        url += `&organization=${this.selectedOrganizationId}`;
      }
      return url;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger: formatInteger,
    async loadPlatforms() {
      if (this.selectedOrganizationId) {
        this.loading = true;
        try {
          let response = await axios.get(this.platformsURL);
          this.platforms = response.data.map((item) => {
            item.interests = createLoadingInterestRecord();
            item.title_count = "loading";
            return item;
          });
          await Promise.all([
            this.loadPlatformInterest(),
            this.loadPlatformTitleCount(),
            this.loadPlatformSushiCounts(),
            this.loadAnnotations(),
          ]);
        } catch (error) {
          this.showSnackbar({
            content: "Error loading platforms: " + error,
            color: "error",
          });
        } finally {
          this.loading = false;
        }
      }
    },
    async loadPlatformInterest() {
      try {
        let response = await axios.get(this.platformInterestURL);
        let pkToRow = {};
        for (let row of response.data) {
          pkToRow[row.platform] = row;
        }
        for (let platform of this.platforms) {
          let newData = pkToRow[platform.pk];
          if (newData) {
            this.$set(platform, "interests", newData);
          } else {
            platform.interests = createEmptyInterestRecord();
          }
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading platform interest: " + error,
          color: "warning",
        });
      }
    },
    async loadPlatformTitleCount() {
      try {
        let response = await axios.get(this.platformTitleCountURL);
        let pkToRow = {};
        for (let row of response.data) {
          pkToRow[row.platform] = row;
        }
        for (let platform of this.platforms) {
          let newData = pkToRow[platform.pk];
          if (newData) {
            platform.title_count = newData.title_count;
          } else {
            platform.title_count = null;
          }
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading platform title count: " + error,
          color: "warning",
        });
      }
    },
    async loadPlatformSushiCounts() {
      if (this.selectedOrganizationId) {
        try {
          let response = await axios.get(
            `/api/organization/${this.selectedOrganizationId}/sushi-credentials-versions/`
          );
          for (let platform of this.platforms) {
            let key = platform.pk.toString();
            if (key in response.data) {
              this.$set(
                platform,
                "sushi_credentials_versions",
                response.data[key]
              );
            } else {
              this.$set(platform, "sushi_credentials_versions", {});
            }
          }
        } catch (error) {
          this.showSnackbar({ content: "Error loading platforms: " + error });
        }
      }
    },
    async loadAnnotations() {
      this.annotations = {};
      try {
        let response = await axios.get(this.annotationsUrl);
        this.annotations = {};
        // populate the this.annotations object
        for (let annot of response.data.filter(
          (item) => item.platform != null
        )) {
          if (!(annot.platform.pk in this.annotations)) {
            this.annotations[annot.platform.pk] = [];
          }
          this.annotations[annot.platform.pk].push(annot);
        }
        // assign annotations to individual platform
        for (let platform of this.platforms) {
          if (platform.pk in this.annotations) {
            this.$set(platform, "annotations", this.annotations[platform.pk]);
          }
        }
      } catch (error) {
        this.showSnackbar({
          content: "Error loading annotations: " + error,
          color: "error",
        });
      }
    },
    refreshAnnotations() {
      this.$refs.annotWidget.fetchAnnotations();
      this.loadAnnotations();
    },
  },
  created() {
    this.loadPlatforms();
  },
  watch: {
    platformsURL() {
      this.loadPlatforms();
    },
    dateRangeStart() {
      this.loadPlatforms();
    },
    dateRangeEnd() {
      this.loadPlatforms();
    },
  },
};
</script>

<style lang="scss">
table.v-table {
  thead {
    th.wrap {
      white-space: normal;
    }
  }
}
</style>
