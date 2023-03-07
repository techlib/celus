<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/notifications.yaml"></i18n>
<i18n lang="yaml" src="@/locales/tours.yaml"></i18n>

<template>
  <v-navigation-drawer
    v-model="show"
    :mini-variant.sync="mini"
    clipped
    app
    mobile-breakpoint="900"
  >
    <v-toolbar flat class="transparent">
      <v-list class="pa-0">
        <v-list-item>
          <v-list-item-action>
            <v-icon>fa-th</v-icon>
          </v-list-item-action>

          <v-list-item-content>
            {{ $t("menu") }}
          </v-list-item-content>

          <v-list-item-action>
            <v-btn icon @click.stop="mini = !mini">
              <v-icon>fa-chevron-left</v-icon>
            </v-btn>
          </v-list-item-action>
        </v-list-item>
      </v-list>
    </v-toolbar>

    <!-- stuff that should be here on xs displays because it is hidden from the app-bar -->
    <OrganizationSelector
      :lang="appLanguage"
      internal-label
      v-if="$vuetify.breakpoint.smAndDown"
    />
    <SelectedDateRangeWidget input-like-label v-if="$vuetify.breakpoint.xs" />

    <v-divider class="d-md-none"></v-divider>

    <!-- the navigation menu itself -->
    <v-list
      class="pt-0"
      dense
      v-for="(group, index) in activeGroups"
      :key="index"
      subheader
    >
      <v-subheader>
        {{ group.title }}
      </v-subheader>

      <MenuListItem
        v-for="item in group.items.filter((item) =>
          item.show == null ? true : item.show
        )"
        :item="item"
        :key="item.title"
        :notifications="notifications"
        :chip="item.chip"
      >
      </MenuListItem>
    </v-list>

    <template #append>
      <div class="pb-3 text-center">
        <v-btn
          v-if="tourName"
          outlined
          v-text="$t(tourToShow.title)"
          color="grey"
          @click="activateTour({ name: tourName })"
        ></v-btn>
      </div>
      <div class="small subdued text-center mb-2">
        <router-link :to="{ name: 'changelog' }">
          {{ $t("celus_version") }}: {{ celusVersion }}
        </router-link>
      </div>
    </template>
  </v-navigation-drawer>
</template>
<script>
import { mapActions, mapGetters, mapState } from "vuex";
import OrganizationSelector from "@/components/selectors/OrganizationSelector";
import SelectedDateRangeWidget from "@/components/SelectedDateRangeWidget";
import MenuListItem from "@/components/util/MenuListItem";

export default {
  name: "SidePanel",
  components: { MenuListItem, SelectedDateRangeWidget, OrganizationSelector },
  props: {
    value: { default: true, type: Boolean },
    tourName: { default: null, required: false, type: String },
  },
  data() {
    return {
      mini: false,
      show: this.value,
    };
  },
  computed: {
    ...mapState({
      user: "user",
      appLanguage: "appLanguage",
    }),
    ...mapGetters({
      organization: "selectedOrganization",
      showAdminStuff: "showAdminStuff",
      showManagementStuff: "showManagementStuff",
      notifications: "getNotifications",
      allowManualDataUpload: "allowManualDataUpload",
      consortialInstall: "consortialInstall",
      tourByName: "tourByName",
      celusVersion: "celusVersion",
      enableTags: "enableTags",
      isRawImportEnabled: "isRawImportEnabled",
    }),
    tourToShow() {
      return this.tourByName(this.tourName);
    },
    groups() {
      return [
        {
          title: this.$i18n.t("pages.content"),
          items: [
            {
              title: this.$i18n.t("pages.dashboard"),
              icon: "fas fa-tachometer-alt",
              linkTo: "dashboard",
            },
            {
              title: this.$i18n.t("pages.organizations"),
              icon: "fa fa-university",
              linkTo: "organization-list",
              show: this.showManagementStuff,
            },
            {
              title: this.$i18n.t("pages.platforms"),
              icon: "far fa-list-alt",
              linkTo: "platform-list",
            },
            {
              title: this.$i18n.t("pages.all_titles"),
              icon: "far fa-copy",
              linkTo: "title-list",
            },
            {
              title: this.$i18n.t("pages.tags"),
              icon: "fa fa-tags",
              show: this.enableTags,
              items: [
                {
                  title: this.$i18n.t("pages.tag_management"),
                  linkTo: "tags",
                },
                {
                  title: this.$i18n.t("pages.title_lists"),
                  linkTo: "tagging-batches",
                },
              ],
            },
            {
              title: this.$i18n.t("pages.interest_overview"),
              icon: "far fa-flag",
              linkTo: "interest-overview",
            },
            {
              title: this.$i18n.t("pages.heatmap"),
              icon: "far fa-map",
              linkTo: "heatmap",
              show: this.consortialInstall,
            },
            {
              title: this.$i18n.t("labels.annotations"),
              icon: "fas fa-pen-fancy",
              linkTo: "annotations",
            },
          ],
          show: true,
        },
        {
          title: this.$i18n.t("pages.analytics"),
          items: [
            {
              title: this.$i18n.t("pages.flexitable"),
              icon: "fa fa-border-all",
              items: [
                {
                  title: this.$i18n.t("pages.create_report"),
                  linkTo: "flexitable",
                },
                {
                  title: this.$i18n.t("pages.flexi_reports"),
                  linkTo: "flexireports",
                },
                {
                  title: this.$t("pages.exports"),
                  linkTo: "exports",
                },
                {
                  title: this.$t("pages.specialized_reports"),
                  linkTo: "specialized-reports",
                  chip: {
                    text: this.$t("labels.new_menu_item"),
                    color: "error",
                  },
                },
              ],
            },
            {
              title: this.$t("pages.subscriptions"),
              icon: "fa fa-layer-group",
              items: [
                {
                  title: this.$i18n.t("pages.overlap_analysis_titles"),
                  icon: "fa fa-layer-group",
                  linkTo: "overlap-analysis",
                },
                {
                  title: this.$i18n.t("pages.overlap_analysis_platforms"),
                  icon: "fa fa-th",
                  linkTo: "platform-overlap-analysis",
                },
                {
                  title: this.$i18n.t("pages.title_list_overlap"),
                  icon: "fa fa-list",
                  linkTo: "title-list-overlap",
                  chip: {
                    text: this.$t("labels.new_menu_item"),
                    color: "error",
                  },
                },
              ],
            },
          ],
          show: true,
        },
        {
          title: this.$i18n.t("pages.data_management"),
          items: [
            {
              title: this.$i18n.t("pages.sushi"),
              icon: "fa fa-cloud-download-alt",
              show: this.showAdminStuff,
              items: [
                {
                  title: this.$i18n.t("pages.sushi_monthly_overview"),
                  icon: "far fa-calendar-check",
                  linkTo: "sushi-monthly-overview",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$i18n.t("pages.sushi_management"),
                  icon: "far fa-arrow-alt-circle-down",
                  linkTo: "sushi-credentials-list",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$t("pages.sushi_fetch_attempts"),
                  icon: "fa-retweet",
                  linkTo: "harvests",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$t("pages.sushi_troubleshooting"),
                  icon: "fa-exclamation-triangle",
                  linkTo: "sushi-troubleshooting",
                  show: this.showAdminStuff,
                },
              ],
            },
            {
              title: this.$t("pages.manual_data_uploads"),
              icon: "fa-upload",
              linkTo: "manual-data-upload-list",
              show: this.showAdminStuff && this.allowManualDataUpload,
            },
            {
              title: this.$t("pages.supported_non_counter_platforms"),
              icon: "fa-file-excel",
              linkTo: "supported-non-counter-platforms",
              show:
                this.showAdminStuff &&
                this.allowManualDataUpload &&
                this.isRawImportEnabled,
            },
          ],
          show: this.showAdminStuff,
        },
        {
          title: this.$i18n.t("pages.admin"),
          icon: "fa fa-tools",
          show: this.showManagementStuff,
          items: [
            {
              title: this.$i18n.t("pages.configuration"),
              icon: "fa fa-tools",
              show: this.showManagementStuff,
              items: [
                {
                  title: this.$i18n.t("pages.management"),
                  icon: "fas fa-tools",
                  linkTo: "management",
                  show: this.showManagementStuff,
                },
                {
                  title: this.$t("pages.maintenance"),
                  icon: "fa fa-toolbox",
                  linkTo: "maintenance",
                  show: this.showManagementStuff,
                },
              ],
            },
          ],
        },
      ];
    },
    activeGroups() {
      return this.groups.filter((group) => group.show);
    },
  },

  methods: {
    ...mapActions({
      activateTour: "activateTour",
    }),
  },

  watch: {
    show() {
      this.$emit("input", this.show);
    },
    value() {
      this.show = this.value;
    },
  },
};
</script>
