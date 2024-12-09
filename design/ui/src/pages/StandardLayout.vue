<i18n lang="yaml" src="@/locales/dialog.yaml" />
<i18n lang="yaml" src="@/locales/common.yaml" />

<i18n lang="yaml">
en:
  releases: CELUS releases
  email_not_verified: Your email is not verified
  impersonated: You are currently impersonating another user.
  context_help_tt: Click for a link to the CELUS knowledge base for this page
  click_for_more_info: Click for more information about the release

cs:
  releases: Vydání CELUSu
  email_not_verified: Vaše emailová adresa není ověřená
  context_help_tt: Kliknutím přejdete na stránku s nápovědou k této stránce
  impersonated: Právě zosobňujete jiného uživatele.
  click_for_more_info: Klikněte pro více informací o vydání
</i18n>

<template>
  <v-app>
    <SidePanel v-model="showSidePanel" />

    <v-app-bar app clipped-left clipped-right>
      <v-toolbar-title class="flex-sm-shrink-0">
        <img
          :src="
            siteLogo
              ? siteLogo.img
              : require('../assets/celus-horizontal-dark.svg')
          "
          :alt="siteLogo ? siteLogo.alt_text : 'CELUS'"
          id="logo-image"
        />
      </v-toolbar-title>

      <v-divider class="mx-3 d-none d-md-block" inset vertical></v-divider>

      <OrganizationSelector
        internal-label
        :lang="appLanguage"
        v-if="showOrganizationSelector"
        class="d-flex"
        :disabled="disableOrganizationSelector"
      />
      <SelectedDateRangeWidget
        input-like-label
        class="d-flex"
        v-if="showDateRangeSelector"
      />

      <v-spacer></v-spacer>

      <v-select
        v-if="showLanguageSelector"
        v-model="appLanguage"
        :items="activeLanguageCodes"
        class="short"
        shrink
      >
        <template #prepend>
          <v-icon class="fs-20">fa-globe</v-icon>
        </template>
      </v-select>

      <!-- user icon -->
      <v-toolbar-items class="align-baseline">
        <v-divider class="mx-3" inset vertical></v-divider>

        <v-badge
          color="error"
          overlap
          :value="unreadEventCount"
          :content="unreadEventCount"
          class="align-self-center mr-2"
        >
          <v-tooltip bottom max-width="600px">
            <template #activator="{ on }">
              <v-btn
                v-on="on"
                icon
                small
                text
                plain
                :to="{
                  name: 'events',
                  query: { sortBy: 'created', sortDesc: true },
                }"
              >
                <v-icon>fa-envelope</v-icon>
              </v-btn>
            </template>
            {{ $t("labels.unread_messages") }}
          </v-tooltip>
        </v-badge>

        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <span v-on="on" class="align-self-center">
              <router-link :to="{ name: 'releases' }">
                <v-badge
                  :value="displayNewReleaseBadge"
                  color="warning"
                  right
                  dot
                  offset-x="16"
                  offset-y="31"
                >
                  <v-icon class="mx-2 fs-20" color="disabled"
                    >fa fa-bullhorn</v-icon
                  >
                </v-badge>
              </router-link>
            </span>
          </template>
          {{ $t("releases") }}
        </v-tooltip>

        <v-tooltip bottom v-if="impersonator">
          <template v-slot:activator="{ on }">
            <v-icon v-on="on" class="mx-1 align-self-center" color="purple"
              >fa-mask</v-icon
            >
          </template>
          {{ $t("impersonated") }}
        </v-tooltip>

        <v-tooltip bottom v-if="!emailVerified">
          <template v-slot:activator="{ on }">
            <span v-on="on" class="align-self-center">
              <router-link :to="{ name: 'user-page' }">
                <v-icon class="mx-1" color="warning"
                  >fa fa-exclamation-triangle</v-icon
                >
              </router-link>
            </span>
          </template>
          {{ $t("email_not_verified") }}
        </v-tooltip>

        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <span v-on="on">
              <router-link :to="{ name: 'user-page' }">
                <v-avatar color="primary" class="mt-2">
                  <v-gravatar
                    v-if="loggedIn && user"
                    :email="user.email"
                    :alt="avatarText"
                    default-img="mp"
                  >
                  </v-gravatar>
                  <v-icon v-else dark>fa-user</v-icon>
                </v-avatar>
              </router-link>
            </span>
          </template>
          <span>{{ usernameText }}</span>
        </v-tooltip>
      </v-toolbar-items>

      <v-btn
        @click.stop="showSidePanel = !showSidePanel"
        icon
        v-if="$vuetify.breakpoint.mobile"
      >
        <v-icon>fa fa-bars</v-icon>
      </v-btn>
    </v-app-bar>

    <!-- we need some empty space at the bottom of each page for the
         floating info button to fit in -->
    <v-main
      v-if="selectedOrganizationId || !showOrganizationSelector"
      class="mb-8"
    >
      <v-alert
        class="ma-4 mt-6"
        v-if="displayNewReleaseAlert"
        @input="dismissLastRelease(false)"
        dense
        dismissible
        outlined
        icon="fa-bullhorn"
        text
        type="success"
      >
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <span v-on="on">
              <router-link :to="{ name: 'releases' }">
                {{
                  latestPublishedRelease.title[appLanguage] ||
                  latestPublishedRelease.title.en
                }}</router-link
              >
            </span>
          </template>
          {{ $t("click_for_more_info") }}
        </v-tooltip>
      </v-alert>
      <v-container fluid pa-0 pa-sm-2>
        <v-tooltip left v-if="showHelpButton">
          <template #activator="{ on }">
            <v-btn
              color="info"
              fab
              small
              fixed
              bottom
              right
              v-on="on"
              target="_blank"
              :href="helpLink"
            >
              <v-icon>fa-question</v-icon>
            </v-btn>
          </template>
          {{ helpText || $t("context_help_tt") }}
        </v-tooltip>

        <router-view :key="$route.fullPath" v-if="loggedIn" />

        <v-snackbar v-model="snackbarShow" :color="snackbarColor">
          {{ snackbarText }}
          <template #action="{ attrs }">
            <v-btn dark text @click="hideSnackbar" v-bind="attrs">{{
              $t("close")
            }}</v-btn>
          </template>
        </v-snackbar>
      </v-container>
    </v-main>

    <v-footer app absolute inset height="128px" v-if="footerImages.length">
      <v-container fluid>
        <v-row no-gutters wrap>
          <v-col
            cols="auto"
            v-for="(image, index) of footerImages"
            :key="index"
          >
            <img :src="image.img" :alt="image.alt_text" class="logow" />
          </v-col>
        </v-row>
      </v-container>
    </v-footer>

    <LoginDialog />
    <CreateOrganizationDialog v-if="showCreateOrganizationDialog" />
  </v-app>
</template>

<script>
import SidePanel from "./SidePanel";
import { mapActions, mapGetters, mapState } from "vuex";
import OrganizationSelector from "@/components/selectors/OrganizationSelector";
import SelectedDateRangeWidget from "@/components/SelectedDateRangeWidget";
import LoginDialog from "@/components/account/LoginDialog";
import VGravatar from "vue-gravatar";
import CreateOrganizationDialog from "@/components/account/CreateOrganizationDialog";
import axios from "axios";

export default {
  name: "Dashboard",
  components: {
    CreateOrganizationDialog,
    LoginDialog,
    SelectedDateRangeWidget,
    OrganizationSelector,
    SidePanel,
    VGravatar,
  },
  data() {
    return {
      navbarExpanded: false,
      showSidePanel: true,
      helpLink: false,
      helpText: "",
    };
  },
  computed: {
    ...mapState({
      snackbarText: "snackbarContent",
      snackbarColor: "snackbarColor",
      selectedOrganizationId: "selectedOrganizationId",
      user: "user",
      latestPublishedRelease: "latestPublishedRelease",
      eventWorker: "eventWorker",
      siteLogo: (state) => state.siteConfig.siteLogo,
      siteName: (state) => state.siteConfig.siteName,
      footerImages: (state) => state.siteConfig.footerImages,
      unreadEventCount: (state) => state.events.unreadCount,
      forceDisableOrganizationSelector: "forceDisableOrganizationSelector",
      forceHideDateRangeSelector: "forceHideDateRangeSelector",
    }),
    ...mapGetters({
      loggedIn: "loggedIn",
      avatarText: "avatarText",
      avatarImg: "avatarImg",
      usernameText: "usernameText",
      emailVerified: "emailVerified",
      impersonator: "impersonator",
      showCreateOrganizationDialog: "showCreateOrganizationDialog",
      activeLanguageCodes: "activeLanguageCodes",
    }),
    displayNewReleaseBadge() {
      if (this.latestPublishedRelease?.version) {
        return (
          this.latestPublishedRelease.version !==
          this.user.extra_data.last_seen_release
        );
      } else {
        return false;
      }
    },
    displayNewReleaseAlert() {
      if (this.latestPublishedRelease?.version) {
        return (
          this.latestPublishedRelease.version !==
          this.user.extra_data.last_dismissed_release
        );
      } else {
        return false;
      }
    },
    snackbarShow: {
      get() {
        return this.$store.state.snackbarShow;
      },
      set(newValue) {
        if (newValue === false) this.hideSnackbar();
      },
    },
    appLanguage: {
      get() {
        return this.$store.state.appLanguage;
      },
      set: async function (newValue) {
        await this.$store.dispatch("setAppLanguage", { lang: newValue });
        this.$router.go();
      },
    },
    showLanguageSelector() {
      return this.activeLanguageCodes.length > 1;
    },
    disableOrganizationSelector() {
      return !!this.forceDisableOrganizationSelector[this.$route.name];
    },
    hideDateRangeSelector() {
      return !!this.forceHideDateRangeSelector[this.$route.name];
    },
    showOrganizationSelector() {
      return (
        this.$vuetify.breakpoint.mdAndUp &&
        !this.$route.meta.hideOrganizationSelector
      );
    },
    showDateRangeSelector() {
      return (
        this.$vuetify.breakpoint.mdAndUp &&
        !this.$route.meta.hideDateRangeSelector &&
        !this.hideDateRangeSelector
      );
    },
    showHelpButton() {
      return !!this.helpLink;
    },
  },

  methods: {
    ...mapActions({
      hideSnackbar: "hideSnackbar",
      dismissLastRelease: "dismissLastRelease",
    }),
    toggleNavbar() {
      this.navbarExpanded = !this.navbarExpanded;
    },
    async fetchHelpLink() {
      try {
        const result = await axios.get(
          `https://spaces.celus.net/help/${this.$route.name}.json`
        );
        this.helpLink = result.data.url;
        this.helpText = result.data.help_text;
      } catch (error) {
        if (error.response?.status !== 404) {
          console.error("Unexpected error getting CDN data: ", error);
        }
      }
    },
  },

  async mounted() {
    this.$i18n.locale = this.appLanguage;
  },

  watch: {
    appLanguage() {
      this.$i18n.locale = this.appLanguage;
    },

    $route: {
      immediate: true,
      handler(to, from) {
        document.title = to.meta?.title
          ? this.$t(to.meta.title) + " – CELUS"
          : "CELUS";
        this.helpLink = null;
        this.fetchHelpLink();
      },
    },
  },
};
</script>

<style lang="scss" scoped>
#logo-image {
  @media only screen and (max-width: 600px) {
    width: 20vw;
  }
  max-width: 128px;
  height: 36px;
}

img.logo {
  max-width: 20vw;
}

img.logow {
  max-height: 92px;
}

.fs-20 {
  font-size: 20px;
  line-height: 28px;
}
</style>
