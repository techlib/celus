<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/notifications.yaml"></i18n>

<template>
  <v-navigation-drawer v-model="show" :mini-variant="mini">
    <!-- stuff that should be here on xs displays because it is hidden from the app-bar -->
    <OrganizationSelector
      :lang="appLanguage"
      internal-label
      v-if="$vuetify.display.smAndDown"
      class="pb-0"
    ></OrganizationSelector>
    <SelectedDateRangeWidget
      input-like-label
      v-if="$vuetify.display.smAndDown"
      class="pl-0"
    ></SelectedDateRangeWidget>
    <v-divider class="d-md-none"></v-divider>
    <!-- the navigation menu itself -->
    <v-list
      class="pa-0"
      density="compact"
      v-for="(group, index) in activeGroups"
      :key="index"
      nav
      :lines="false"
    >
      <v-list-subheader class="mt-3 pl-0">
        {{ group.title }}
      </v-list-subheader>
      <MenuListItem
        v-for="item in group.items.filter((item) =>
          item.show == null ? true : item.show,
        )"
        :item="item"
        :key="item.title"
        :notifications="notifications"
        :chip="item.chip"
      >
      </MenuListItem>
    </v-list>
    <template #append>
      <div class="small subdued text-center mb-2">
        <router-link :to="{ name: 'changelog' }">
          {{ $t("celus_version") }}: {{ celusVersion }}
        </router-link>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script>
import { mapGetters, mapState } from "vuex";
import OrganizationSelector from "@/components/selectors/OrganizationSelector";
import SelectedDateRangeWidget from "@/components/SelectedDateRangeWidget";
import MenuListItem from "@/components/util/MenuListItem";

import { useDisplay } from "vuetify";

export default {
  name: "SidePanel",
  components: { MenuListItem, SelectedDateRangeWidget, OrganizationSelector },
  props: {
    modelValue: { default: true, type: Boolean },
  },
  data() {
    return {
      mini: false,
      show: this.modelValue,
    };
  },
  computed: {
    // xs,
    // smAndDown,
    ...mapState({
      user: "user",
      appLanguage: "appLanguage",
    }),
    ...mapGetters({
      organization: "selectedOrganization",
      showAdminStuff: "showAdminStuff",
      showManagementStuff: "showManagementStuff",
      notifications: "getNotifications",
      consortialInstall: "consortialInstall",
      celusVersion: "celusVersion",
      isRawImportEnabled: "isRawImportEnabled",
      allowUserManagement: "allowUserManagement",
    }),
    isSuperuser() {
      return this.user && this.user.is_superuser;
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
                    title: this.$t("labels.new_menu_item"),
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
                  // icon: "fa fa-layer-group",
                  linkTo: "overlap-analysis",
                },
                {
                  title: this.$i18n.t("pages.overlap_analysis_platforms"),
                  // icon: "fa fa-th",
                  linkTo: "platform-overlap-analysis",
                },
                {
                  title: this.$i18n.t("pages.title_list_overlap"),
                  // icon: "fa fa-list",
                  linkTo: "title-list-overlap",
                  chip: {
                    title: this.$t("labels.new_menu_item"),
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
                  // icon: "far fa-calendar-check",
                  linkTo: "sushi-monthly-overview",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$i18n.t("pages.sushi_management"),
                  // icon: "far fa-arrow-alt-circle-down",
                  linkTo: "sushi-credentials-list",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$t("pages.sushi_fetch_attempts"),
                  // icon: "fa fa-retweet",
                  linkTo: "harvests",
                  show: this.showAdminStuff,
                },
                {
                  title: this.$t("pages.sushi_troubleshooting"),
                  // icon: "fa fa-exclamation-triangle",
                  linkTo: "sushi-troubleshooting",
                  show: this.showAdminStuff,
                },
              ],
            },
            {
              title: this.$t("pages.manual_data_uploads"),
              icon: "fa fa-upload",
              linkTo: "manual-data-upload-list",
              show: this.showAdminStuff,
            },
            {
              title: this.$t("pages.supported_non_counter_platforms"),
              icon: "fas fa-file-excel",
              linkTo: "supported-non-counter-platforms",
              chip: {
                title: this.$t("labels.new_menu_item"),
                color: "error",
              },
              show: this.showAdminStuff && this.isRawImportEnabled,
            },
            {
              title: this.$t("pages.data_coverage_overview"),
              icon: "fa fa-sitemap",
              linkTo: "data-coverage-overview",
              chip: {
                title: this.$t("labels.new_menu_item"),
                color: "error",
              },
              show: true,
            },
          ],
          show: true,
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
                  // icon: "fas fa-tools",
                  linkTo: "management",
                  show: this.showManagementStuff,
                },
                {
                  title: this.$t("pages.maintenance"),
                  // icon: "fa fa-toolbox",
                  linkTo: "maintenance",
                  show: this.showManagementStuff,
                },
                {
                  title: this.$t("pages.management_commands"),
                  // icon: "fa fa-terminal",
                  linkTo: "management-commands",
                  show: this.isSuperuser,
                },
              ],
            },
          ],
        },
        {
          title: this.$i18n.t("pages.organization_administration"),
          icon: "fa fa-tools",
          show: this.allowUserManagement,
          items: [
            {
              title: this.$i18n.t("pages.account_management"),
              icon: "fa fa-user",
              linkTo: "account-management",
              show: this.allowUserManagement,
            },
          ],
        },
        {
          title: this.$i18n.t("pages.whats_new"),
          icon: "fa fa-info-circle",
          show: true,
          items: [
            {
              title: this.$i18n.t("pages.events"),
              icon: "fa fa-envelope",
              linkTo: "events",
            },
            {
              title: this.$i18n.t("pages.releases"),
              icon: "fa fa-broadcast-tower",
              linkTo: "releases",
            },
            {
              title: this.$i18n.t("pages.changelog"),
              icon: "fa fa-list",
              linkTo: "changelog",
            },
          ],
        },
      ];
    },
    activeGroups() {
      return this.groups.filter((group) => group.show);
    },
  },

  watch: {
    show() {
      this.$emit("update:modelValue", this.show);
    },
    modelValue() {
      this.show = this.modelValue;
    },
  },
  setup(props, { emit }) {
    const { xs, smAndDown, md } = useDisplay();
    return {
      xs,
      smAndDown,
      md,
    };
  },
  mounted() {},
};
</script>
