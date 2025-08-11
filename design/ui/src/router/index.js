// Composables
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    name: "home",
    redirect: { name: "dashboard" },
  },
  {
    path: "/verify-email/",
    name: "verify-email",
    component: () => import("../pages/VerifyEmailPage.vue"),
    meta: {
      outsideNormalLayout: true,
    },
  },
  {
    path: "/reset-password/",
    name: "reset-password",
    component: () => import("../pages/PasswordResetPage.vue"),
    meta: {
      outsideNormalLayout: true,
      invitation: false,
    },
  },
  {
    path: "/accept-invitation/",
    name: "accept-invitation",
    component: () => import("../pages/PasswordResetPage.vue"),
    meta: {
      outsideNormalLayout: true,
      invitation: true,
    },
  },
  // {
  //   path: "/intro/",
  //   name: "intro",
  //   component: () => import("../pages/IntroPage.vue"),
  // },
  {
    path: "/dashboard/",
    name: "dashboard",
    component: () => import("@/pages/DashboardPage.vue"),
    meta: {
      title: "pages.dashboard",
    },
  },
  {
    path: "/user/",
    name: "user-page",
    component: () => import("../pages/UserPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.user_page",
    },
  },
  {
    path: "/platforms/",
    name: "platform-list",
    component: () => import("../pages/PlatformListPage.vue"),
    meta: {
      title: "pages.platforms",
    },
  },
  {
    path: "/organizations/",
    name: "organization-list",
    component: () => import("../pages/OrganizationListPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.organizations",
    },
  },
  {
    path: "/titles/",
    name: "title-list",
    component: () => import("../pages/AllTitlesListPage.vue"),
    meta: {
      title: "pages.all_titles",
    },
  },
  {
    path: "/platforms/:platformId",
    name: "platform-detail",
    component: () => import("../pages/PlatformDetailPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
    }),
    meta: {
      title: "pages.platform_detail",
    },
  },
  {
    path: "/platforms/:platformId/title/:titleId",
    name: "platform-title-detail",
    component: () => import("../pages/TitleDetailPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
      titleId: Number.parseInt(route.params.titleId, 10),
    }),
    meta: {
      title: "pages.title_detail",
    },
  },
  {
    path: "/titles/:titleId",
    name: "title-detail",
    component: () => import("../pages/TitleDetailPage.vue"),
    props: (route) => ({
      platformId: null,
      titleId: Number.parseInt(route.params.titleId, 10),
    }),
    meta: {
      title: "pages.title_detail",
    },
  },
  {
    path: "/platforms/:platformId/title/:titleId/item/:itemId",
    name: "platform-title-item-detail",
    component: () => import("../pages/ItemDetailPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
      titleId: Number.parseInt(route.params.titleId, 10),
      itemId: Number.parseInt(route.params.itemId, 10),
    }),
    meta: {
      title: "pages.item_detail",
    },
  },
  {
    path: "/titles/:titleId/item/:itemId",
    name: "title-item-detail",
    component: () => import("../pages/ItemDetailPage.vue"),
    props: (route) => ({
      platformId: null,
      titleId: Number.parseInt(route.params.titleId, 10),
      itemId: Number.parseInt(route.params.itemId, 10),
    }),
    meta: {
      title: "pages.item_detail",
    },
  },
  {
    path: "/platforms/:platformId/item/:itemId",
    name: "platform-item-detail",
    component: () => import("../pages/ItemDetailPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
      itemId: Number.parseInt(route.params.itemId, 10),
    }),
    meta: {
      title: "pages.item_detail",
    },
  },
  {
    path: "/interests",
    name: "interest-overview",
    component: () => import("../pages/InterestOverviewPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.interest_overview",
    },
  },
  {
    path: "/tags",
    name: "tags",
    component: () => import("../pages/TagListPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.tag_management",
    },
  },
  {
    path: "/tagging-batches",
    name: "tagging-batches",
    component: () => import("../pages/TaggingBatchesPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.title_lists",
    },
  },
  //
  {
    path: "/releases",
    name: "releases",
    component: () => import("../pages/ReleasesPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.releases",
    },
  },
  {
    path: "/changelog",
    name: "changelog",
    component: () => import("../pages/ChangeLogPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.changelog",
    },
  },
  {
    path: "/heatmap",
    name: "heatmap",
    component: () =>
      import("../pages/OrganizationPlatformInterestOverviewPage.vue"),
    meta: {
      title: "pages.heatmap",
    },
  },
  {
    path: "/annotations/",
    name: "annotations",
    component: () => import("../pages/AnnotationListPage.vue"),
    meta: {
      title: "labels.annotations",
    },
  },
  {
    path: "/account-management/",
    name: "account-management",
    component: () => import("../pages/AccountManagementPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.account_management",
    },
  },
  {
    path: "/counter-registry/",
    name: "counter-registry",
    component: () => import("../pages/CounterRegistry.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.counter_registry",
    },
  },
  {
    path: "/analytics/overlap",
    name: "overlap-analysis",
    component: () => import("../pages/OverlapAnalysisPage.vue"),
    meta: {
      title: "pages.overlap_analysis_titles",
    },
  },
  {
    path: "/analytics/platform-overlap",
    name: "platform-overlap-analysis",
    component: () => import("../pages/PlatformOverlapAnalysisPage"),
    meta: {
      title: "pages.overlap_analysis_platforms",
    },
  },
  {
    path: "/analytics/title-list-overlap",
    name: "title-list-overlap",
    component: () => import("../pages/TitleListOverlapPage"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.title_list_overlap",
    },
  },
  {
    path: "/analytics/flexitable",
    name: "flexitable",
    component: () => import("../pages/FlexiTablePage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.create_report",
    },
  },
  {
    path: "/analytics/flexible-reports/:reportId",
    name: "flexireport",
    component: () => import("../pages/FlexiTablePage.vue"),
    props: (route) => ({
      reportId: Number.parseInt(route.params.reportId, 10),
    }),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.flexi_report",
    },
  },
  {
    path: "/analytics/flexible-reports",
    name: "flexireports",
    component: () => import("../pages/FlexibleReportsPage.vue"),
    meta: {
      hideOrganizationSelector: false, // the page will hide it depending on internal logic
      hideDateRangeSelector: false, // the page will hide it depending on internal logic
      title: "pages.flexi_reports",
    },
  },
  {
    path: "/analytics/exports",
    name: "exports",
    component: () => import("../pages/ExportOverviewPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.exports",
    },
  },
  {
    path: "/analytics/anomaly-report",
    name: "anomaly-report",
    component: () => import("../pages/AnomalyReportPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.anomaly_report",
    },
  },
  {
    path: "/admin/management/",
    name: "management",
    component: () => import("../pages/ManagementPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.management",
    },
  },
  {
    path: "/admin/sushi-credentials/",
    name: "sushi-credentials-list",
    component: () => import("../pages/SushiCredentialsManagementPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.sushi_management",
    },
  },
  {
    path: "/admin/sushi-by-month/",
    name: "sushi-monthly-overview",
    component: () => import("../pages/SushiCredentialsMonthOverviewPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.sushi_monthly_overview",
    },
  },
  {
    path: "/admin/sushi-troubleshooting/",
    name: "sushi-troubleshooting",
    component: () => import("../pages/SushiTroubleshootingPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      hideOrganizationSelector: true,
      title: "pages.sushi_troubleshooting",
    },
  },
  {
    path: "/admin/mdu/",
    name: "manual-data-upload-list",
    component: () => import("../pages/ManualUploadListPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.manual_data_uploads",
    },
  },
  {
    path: "/admin/non-counter-platforms/",
    name: "supported-non-counter-platforms",
    component: () => import("../pages/SupportedNonCounterPlatformsPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.supported_non_counter_platforms",
    },
  },
  {
    path: "/admin/harvests/",
    name: "harvests",
    component: () => import("../pages/HarvestsPage.vue"),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.sushi_fetch_attempts",
    },
  },
  {
    path: "/admin/maintenance/",
    name: "maintenance",
    component: () => import("../pages/MaintenancePage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.maintenance",
    },
  },
  {
    path: "/admin/commands/",
    name: "management-commands",
    component: () => import("../pages/ManagementCommandsPage.vue"),
    meta: {
      hideOrganizationSelector: true,
      hideDateRangeSelector: true,
      title: "pages.management_commands",
    },
  },
  {
    path: "/admin/data-coverage/",
    name: "data-coverage-overview",
    component: () => import("../pages/DataCoverageOverviewPage.vue"),
    meta: {
      title: "pages.data_coverage_overview",
    },
  },
  {
    path: "/admin/ch-export/",
    name: "ch-export",
    component: () => import("../pages/ChExportPage.vue"),
    meta: {
      title: "pages.ch_export",
    },
  },
  {
    path: "/platforms/:platformId/upload-data/",
    name: "platform-upload-data",
    component: () => import("../pages/CustomDataUploadPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
    }),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.mdu_detail",
    },
  },
  {
    path: "/platforms/:platformId/upload-data/:uploadObjectId",
    name: "platform-upload-data-step-preflight",
    component: () => import("../pages/CustomDataUploadPage.vue"),
    props: (route) => ({
      platformId: Number.parseInt(route.params.platformId, 10),
      uploadObjectId: Number.parseInt(route.params.uploadObjectId, 10),
    }),
    meta: {
      hideDateRangeSelector: true,
      title: "pages.mdu_detail",
    },
  },
  {
    path: "/specialized-reports",
    name: "specialized-reports",
    component: () => import("../pages/SpecializedReportsPage.vue"),
    meta: {
      title: "pages.specialized_reports",
    },
  },
  {
    path: "/events",
    name: "events",
    component: () => import("../pages/EventsPage.vue"),
    meta: {
      title: "pages.events",
    },
  },

  //  {
  //    path: "/secure",
  //    name: "after-login-page",
  //    component: () => import("../pages/AfterLoginPage.vue"),
  // },
  {
    path: "/goto/:name",
    redirect: (to) => {
      return {
        name: to.params.name,
      };
    },
  },

  {
    path: "/:catchAll(.*)",
    component: () => import("../pages/NotFoundPage.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  mode: "history",
  linkActiveClass: "is-active",

  routes,
});

export default router;
