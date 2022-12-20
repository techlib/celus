<template>
  <v-card>
    <v-card-text>
      <v-btn-toggle v-model="viewType" class="float-sm-right">
        <v-btn value="interest" small>
          <v-icon small>fa fa-list</v-icon>
        </v-btn>
        <v-btn value="chart" small>
          <v-icon small>fa fa-chart-bar</v-icon>
        </v-btn>
        <v-btn value="cost" small>
          <v-icon small>fa fa-dollar-sign</v-icon>
        </v-btn>
      </v-btn-toggle>

      <div v-if="viewType === 'chart'" class="pt-10" style="min-height: 70vh">
        <PlatformInterestChart :platforms="platforms">
          <v-btn :href="platformInterestURL + '&format=csv'" color="secondary">
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
          @update-platforms="loadPlatforms"
        />
      </div>
    </v-card-text>
  </v-card>
</template>
<script>
import InterestGroupSelector from "@/components/selectors/InterestGroupSelector";
import PlatformCostList from "@/components/PlatformCostList";
import PlatformInterestChart from "@/components/PlatformInterestChart";
import PlatformList from "@/components/PlatformList";
import { mapActions, mapGetters, mapState } from "vuex";
import { formatInteger } from "@/libs/numbers";
import {
  createEmptyInterestRecord,
  createLoadingInterestRecord,
} from "@/libs/interest";
import cancellation from "@/mixins/cancellation";

export default {
  name: "PlatformOverviewWidget",

  mixins: [cancellation],

  components: {
    InterestGroupSelector,
    PlatformCostList,
    PlatformInterestChart,
    PlatformList,
  },

  props: {},

  data() {
    return {
      platforms: [],
      loading: false,
      viewType: "interest",
      annotations: {},
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
        let { response, error } = await this.http({ url: this.platformsURL });
        if (!error) {
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
        } else {
          this.showSnackbar({
            content: "Error loading platforms: " + error,
            color: "error",
          });
        }
        this.loading = false;
        this.$emit("loaded");
      }
    },
    async loadPlatformInterest() {
      let { response, error } = await this.http({
        url: this.platformInterestURL,
      });
      if (!error) {
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
      } else {
        this.showSnackbar({
          content: "Error loading platform interest: " + error,
          color: "warning",
        });
      }
    },
    async loadPlatformTitleCount() {
      let { response, error } = await this.http({
        url: this.platformTitleCountURL,
      });
      if (!error) {
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
      } else {
        this.showSnackbar({
          content: "Error loading platform title count: " + error,
          color: "warning",
        });
      }
    },
    async loadPlatformSushiCounts() {
      if (this.selectedOrganizationId) {
        let { response, error } = await this.http({
          url: `/api/organization/${this.selectedOrganizationId}/sushi-credentials-versions/`,
        });
        if (!error) {
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
        } else {
          this.showSnackbar({
            content: "Error loading platforms: " + error,
            color: "error",
          });
        }
      }
    },
    async loadAnnotations() {
      this.annotations = {};
      let { response, error } = await this.http({ url: this.annotationsUrl });
      if (!error) {
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
      } else {
        this.showSnackbar({
          content: "Error loading annotations: " + error,
          color: "error",
        });
      }
    },
    refreshAnnotations() {
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
