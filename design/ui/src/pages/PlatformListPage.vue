<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  default: Platform overview - default view
  view: View

cs:
  default: Přehled platforem - výchozí pohled
  view: Pohled
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0" cols="auto">
        <h2>{{ $t("pages.platforms") }}</h2>
      </v-col>
      <v-col cols="auto">
        <v-select
          v-model="viewId"
          :items="views"
          :label="$t('view')"
          outlined
          dense
        ></v-select>
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
            <v-col cols="auto" class="pa-1" v-if="allowManualDataUpload">
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
        <PlatformOverviewWidget
          ref="overviewWidget"
          v-show="viewId === 0"
          @loaded="overviewLoaded"
        />
        <v-card>
          <v-card-text>
            <FlexiTableOutput
              ref="flexiTableWidget"
              v-show="viewId > 0"
              context-override
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters, mapState } from "vuex";
import AnnotationsWidget from "@/components/AnnotationsWidget";
import AddAnnotationButton from "@/components/AddAnnotationButton";
import AddPlatformButton from "@/components/AddPlatformButton";
import ManualUploadButton from "@/components/ManualUploadButton";
import cancellation from "@/mixins/cancellation";
import PlatformOverviewWidget from "@/pages/PlatformOverviewWidget";
import { FlexiReport } from "@/libs/flexi-reports";
import FlexiTableOutput from "@/components/reporting/FlexiTableOutput";

export default {
  name: "PlatformListPage",

  mixins: [cancellation],

  components: {
    FlexiTableOutput,
    PlatformOverviewWidget,
    ManualUploadButton,
    AnnotationsWidget,
    AddAnnotationButton,
    AddPlatformButton,
  },
  data() {
    return {
      loading: false,
      reports: [],
      viewId: 0,
    };
  },
  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      showAdminStuff: "showAdminStuff",
      allowManualDataUpload: "allowManualDataUpload",
      allowUserCreatePlatforms: "allowUserCreatePlatforms",
    }),
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    views() {
      return [
        { text: this.$t("default"), value: 0 },
        ...this.reports.map((report) => {
          return { text: report.name, value: report.pk };
        }),
      ];
    },
    selectedReport() {
      if (this.viewId === 0) {
        return null;
      }
      return this.reports.find((report) => report.pk === this.viewId);
    },
  },
  methods: {
    async loadStoredReports() {
      this.loading = true;
      let { response, error } = await this.http({
        url: "/api/flexible-report/?primary_dimension=platform",
      });
      if (!error) {
        this.reports = response.data;
      } else {
        this.showSnackbar({
          content: "Could not load the list of stored reports",
          color: "error",
        });
      }
      this.loading = false;
    },
    loadPlatforms() {
      if (this.$refs.overviewWidget) {
        this.$refs.overviewWidget.loadPlatforms();
      }
    },
    refreshAnnotations() {
      this.$refs.annotWidget.fetchAnnotations();
      if (this.$refs.overviewWidget) {
        this.$refs.overviewWidget.refreshAnnotations();
      }
    },
    overviewLoaded() {
      this.loadStoredReports();
    },
  },

  watch: {
    async viewId() {
      if (this.viewId > 0 && this.selectedReport) {
        console.log("Loading report", this.selectedReport);
        let report = await FlexiReport.fromAPIObject(
          this.selectedReport,
          this.reportTypeMap
        );
        await this.$refs.flexiTableWidget.updateOutput(report);
      }
    },
  },
};
</script>
