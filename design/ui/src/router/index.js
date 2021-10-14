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
    },
    {
      path: "/platforms/",
      name: "platform-list",
      component: () => import("../pages/PlatformListPage.vue"),
      // meta: {title: 'pages.platforms'}
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
      path: "/heatmap",
      name: "heatmap",
      component: () =>
        import("../pages/OrganizationPlatformInterestOverviewPage.vue"),
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
    },
    {
      path: "/analytics/flexible-reports/:reportId",
      name: "flexireport",
      component: () => import("../pages/FlexiTablePage.vue"),
      props: (route) => ({
        reportId: Number.parseInt(route.params.reportId, 10),
      }),
    },
    {
      path: "/analytics/flexible-reports",
      name: "flexireports",
      component: () => import("../pages/FlexibleReportsPage.vue"),
    },
    {
      path: "/analytics/exports",
      name: "exports",
      component: () => import("../pages/ExportOverviewPage.vue"),
    },
    {
      path: "/admin/management/",
      name: "management",
      component: () => import("../pages/ManagementPage.vue"),
    },
    {
      path: "/admin/sushi-credentials/",
      name: "sushi-credentials-list",
      component: () => import("../pages/SushiCredentialsManagementPage.vue"),
    },
    {
      path: "/admin/sushi-by-month/",
      name: "sushi-monthly-overview",
      component: () => import("../pages/SushiCredentialsMonthOverviewPage.vue"),
    },
    {
      path: "/admin/import-batches/",
      name: "import-batch-list",
      component: () => import("../pages/ImportBatchesPage.vue"),
    },
    {
      path: "/admin/mdu/",
      name: "manual-data-upload-list",
      component: () => import("../pages/ManualUploadListPage.vue"),
    },
    {
      path: "/admin/harvests/",
      name: "harvests",
      component: () => import("../pages/HarvestsPage.vue"),
    },
    {
      path: "/admin/maintenance/",
      name: "maintenance",
      component: () => import("../pages/MaintenancePage.vue"),
    },
    {
      path: "/platforms/:platformId/upload-data/",
      name: "platform-upload-data",
      component: () => import("../pages/CustomDataUploadPage.vue"),
      props: (route) => ({
        platformId: Number.parseInt(route.params.platformId, 10),
      }),
    },
    {
      path: "/platforms/:platformId/upload-data/:uploadObjectId",
      name: "platform-upload-data-step2",
      component: () => import("../pages/CustomDataUploadPage.vue"),
      props: (route) => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        uploadObjectId: Number.parseInt(route.params.uploadObjectId, 10),
      }),
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
