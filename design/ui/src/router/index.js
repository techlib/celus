import Vue from 'vue'
import Router from 'vue-router'
import NotFoundPage from '../pages/NotFoundPage'
// import ChartTestPage from '../pages/ChartTestPage'
import PlatformListPage from '../pages/PlatformListPage'
import PlatformDetailPage from '../pages/PlatformDetailPage'
import TitleDetailPage from '../pages/TitleDetailPage'
import AllTitlesListPage from '../pages/AllTitlesListPage'
import AfterLoginPage from '../pages/AfterLoginPage'
import SushiCredentialsManagementPage from '../pages/SushiCredentialsManagementPage'
import ImportBatchesPage from '../pages/ImportBatchesPage'
import CustomDataUploadPage from '../pages/CustomDataUploadPage'
import SushiFetchAttemptsPage from '../pages/SushiFetchAttemptsPage'
import UserPage from '../pages/UserPage'
import ManagementPage from '../pages/ManagementPage'
import MaintenancePage from '../pages/MaintenancePage'
import OrganizationPlatformInterestOverviewPage
  from '../pages/OrganizationPlatformInterestOverviewPage'
import ManualUploadListPage from '../pages/ManualUploadListPage'
import DashboardPage from '../pages/DashboardPage'
import VerifyEmailPage from '../pages/VerifyEmailPage'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: {name: 'dashboard'},
    },
    {
      path: '/verify-email/',
      name: 'verify-email',
      component: VerifyEmailPage,
      meta: {
        outsideNormalLayout: true,
      }
    },
    {
      path: '/dashboard/',
      name: 'dashboard',
      component: DashboardPage,
    },
    {
      path: '/user/',
      name: 'user-page',
      component: UserPage,
    },
    {
      path: '/platforms/',
      name: 'platform-list',
      component: PlatformListPage,
      // meta: {title: 'pages.platforms'}
    },
    {
      path: '/titles/',
      name: 'title-list',
      component: AllTitlesListPage
    },
    {
      path: '/platforms/:platformId',
      name: 'platform-detail',
      component: PlatformDetailPage,
      props: route => ({platformId: Number.parseInt(route.params.platformId, 10)})
    },
    {
      path: '/platforms/:platformId/title/:titleId',
      name: 'platform-title-detail',
      component: TitleDetailPage,
      props: route => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        titleId: Number.parseInt(route.params.titleId, 10),
      }),
    },
    {
      path: '/titles/:titleId',
      name: 'title-detail',
      component: TitleDetailPage,
      props: route => ({
        platformId: null,
        titleId: Number.parseInt(route.params.titleId, 10),
      })
    },
    {
      path: '/heatmap',
      name: 'heatmap',
      component: OrganizationPlatformInterestOverviewPage,
    },
    {
      path: '/admin/management/',
      name: 'management',
      component: ManagementPage,
    },
    {
      path: '/admin/sushi-credentials/',
      name: 'sushi-credentials-list',
      component: SushiCredentialsManagementPage,
    },
    {
      path: '/admin/import-batches/',
      name: 'import-batch-list',
      component: ImportBatchesPage,
    },
    {
      path: '/admin/mdu/',
      name: 'manual-data-upload-list',
      component: ManualUploadListPage,
    },
    {
      path: '/admin/sushi-fetch-attempts/',
      name: 'sushi-fetch-attempts',
      component: SushiFetchAttemptsPage,
    },
    {
      path: '/admin/maintenance/',
      name: 'maintenance',
      component: MaintenancePage,
    },
    {
      path: '/platforms/:platformId/upload-data/',
      name: 'platform-upload-data',
      component: CustomDataUploadPage,
      props: route => ({platformId: Number.parseInt(route.params.platformId, 10)})
    },
    {
      path: '/platforms/:platformId/upload-data/:uploadObjectId',
      name: 'platform-upload-data-step2',
      component: CustomDataUploadPage,
      props: route => ({
        platformId: Number.parseInt(route.params.platformId, 10),
        uploadObjectId: Number.parseInt(route.params.uploadObjectId, 10),
      })
    },
    {
      path: '/secure',
      name: 'after-login-page',
      component: AfterLoginPage,
    },

    {
      path: '*',
      component: NotFoundPage,
    }
  ],
  mode: 'history',
  linkActiveClass: 'is-active'
})
