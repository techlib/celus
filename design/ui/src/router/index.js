import Vue from "vue";
import Router from "vue-router";

Vue.use(Router);

export default new Router({
  routes: [
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
    {
      path: "/intro/",
      name: "intro",
      component: () => import("../pages/IntroPage.vue"),
    },
    {
      path: "/dashboard/",
      name: "dashboard",
      component: () => import("../pages/DashboardPage.vue"),
    },
    {
      path: "/user/",
      name: "user-page",
      component: () => import("../pages/UserPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/platforms/",
      name: "platform-list",
      component: () => import("../pages/PlatformListPage.vue"),
    },
    {
      path: "/organizations/",
      name: "organization-list",
      component: () => import("../pages/OrganizationListPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/titles/",
      name: "title-list",
      component: () => import("../pages/AllTitlesListPage.vue"),
    },
    {
      path: "/platforms/:platformId",
      name: "platform-detail",
      component: () => import("../pages/PlatformDetailPage.vue"),
      props: (route) => ({
        platformId: Number.parseInt(route.params.platformId, 10),
      }),
    },
    {
      path: "/platforms/:platformId/title/:titleId",
      name: "platform-title-detail",
      component: () => import("../pages/TitleDetailPage.vue"),
      props: (route) => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        titleId: Number.parseInt(route.params.titleId, 10),
      }),
    },
    {
      path: "/titles/:titleId",
      name: "title-detail",
      component: () => import("../pages/TitleDetailPage.vue"),
      props: (route) => ({
        platformId: null,
        titleId: Number.parseInt(route.params.titleId, 10),
      }),
    },
    {
      path: "/interests",
      name: "interest-overview",
      component: () => import("../pages/InterestOverviewPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/tags",
      name: "tags",
      component: () => import("../pages/TagListPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/tagging-batches",
      name: "tagging-batches",
      component: () => import("../pages/TaggingBatchesPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/heatmap",
      name: "heatmap",
      component: () =>
        import("../pages/OrganizationPlatformInterestOverviewPage.vue"),
    },
    {
      path: "/annotations/",
      name: "annotations",
      component: () => import("../pages/AnnotationListPage.vue"),
    },
    {
      path: "/analytics/overlap",
      name: "overlap-analysis",
      component: () => import("../pages/OverlapAnalysisPage.vue"),
    },
    {
      path: "/analytics/platform-overlap",
      name: "platform-overlap-analysis",
      component: () => import("../pages/PlatformOverlapAnalysisPage"),
    },
    {
      path: "/analytics/flexitable",
      name: "flexitable",
      component: () => import("../pages/FlexiTablePage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
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
      },
    },
    {
      path: "/analytics/flexible-reports",
      name: "flexireports",
      component: () => import("../pages/FlexibleReportsPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/analytics/exports",
      name: "exports",
      component: () => import("../pages/ExportOverviewPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/management/",
      name: "management",
      component: () => import("../pages/ManagementPage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/sushi-credentials/",
      name: "sushi-credentials-list",
      component: () => import("../pages/SushiCredentialsManagementPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/sushi-by-month/",
      name: "sushi-monthly-overview",
      component: () => import("../pages/SushiCredentialsMonthOverviewPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/mdu/",
      name: "manual-data-upload-list",
      component: () => import("../pages/ManualUploadListPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/harvests/",
      name: "harvests",
      component: () => import("../pages/HarvestsPage.vue"),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/admin/maintenance/",
      name: "maintenance",
      component: () => import("../pages/MaintenancePage.vue"),
      meta: {
        hideOrganizationSelector: true,
        hideDateRangeSelector: true,
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
      },
    },
    {
      path: "/platforms/:platformId/upload-data/:uploadObjectId",
      name: "platform-upload-data-step2",
      component: () => import("../pages/CustomDataUploadPage.vue"),
      props: (route) => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        uploadObjectId: Number.parseInt(route.params.uploadObjectId, 10),
      }),
      meta: {
        hideDateRangeSelector: true,
      },
    },
    {
      path: "/secure",
      name: "after-login-page",
      component: () => import("../pages/AfterLoginPage.vue"),
    },

    {
      path: "*",
      component: () => import("../pages/NotFoundPage.vue"),
    },
  ],
  mode: "history",
  linkActiveClass: "is-active",
});
