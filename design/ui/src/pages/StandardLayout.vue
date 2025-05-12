<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  releases: CELUS releases
  email_not_verified: Your email is not verified
  impersonated: You are currently impersonating another user.
  context_help_tt: Click for a link to the CELUS knowledge base for this page
  click_for_more_info: Click for more information about the release
  knowledge_base: Knowledge base
cs:
  releases: Vydání CELUSu
  email_not_verified: Vaše emailová adresa není ověřená
  context_help_tt: Kliknutím přejdete na stránku s nápovědou k této stránce
  impersonated: Právě zosobňujete jiného uživatele.
  click_for_more_info: Klikněte pro více informací o vydání
  knowledge_base: Informační báze
</i18n>

<template>
  <v-app>
    <SidePanel v-model="showSidePanel" order="2"></SidePanel>
    <v-app-bar
      color="defaultButton"
      order="1"
      density="compact"
      class="pr-4 pl-4 pt-1 pb-1"
    >
      <template v-slot:prepend>
        <v-btn
          @click.stop="showSidePanel = !showSidePanel"
          icon
          class="mr-2"
          v-if="$vuetify.display.mobile"
        >
          <v-icon icon="fa fa-bars" color="lighterIcons"></v-icon>
        </v-btn>
        <v-toolbar-title class="flex-sm-shrink-0">
          <img
            :src="siteLogo ? siteLogo.img : defaultLogoHorizontal"
            class="logo pt-1"
            :alt="siteLogo ? siteLogo.alt_text : 'CELUS'"
            id="logo-image"
          />
        </v-toolbar-title>
      </template>
      <v-divider class="mx-3 d-none d-md-block" inset vertical></v-divider>
      <v-row align="center" justify="start" style="width: 100%">
        <v-col
          cols="6"
          lg="4"
          md="4"
          align-self="auto"
          class="organization_selector"
        >
          <OrganizationSelector
            internal-label
            :lang="appLanguage"
            style="width: 250px"
            v-if="showOrganizationSelector"
            class="ml-0"
            :disabled="disableOrganizationSelector"
          ></OrganizationSelector>
        </v-col>
        <v-col cols="6" lg="8" md="8">
          <SelectedDateRangeWidget
            input-like-label
            class="d-flex"
            v-if="showDateRangeSelector"
          ></SelectedDateRangeWidget>
        </v-col>
      </v-row>
      <v-spacer></v-spacer>
      <v-select
        v-if="showLanguageSelector"
        v-model="appLanguage"
        :items="activeLanguageCodes"
        class="short"
        min-width="90px"
        width="90px"
        shrink
      >
        <template #prepend>
          <v-icon size="small" class="pt-1" color="lighterGreyIcons"
            >fa fa-globe</v-icon
          >
        </template>
      </v-select>
      <!-- user icon -->
      <v-toolbar-items class="align-center">
        <v-divider class="mx-3" inset vertical></v-divider>
        <v-badge
          color="error"
          overlap
          :content="unreadEventCount"
          class="align-self-center mr-2"
          :value="unreadEventCount"
        >
          <v-tooltip max-width="600px" location="bottom">
            <template #activator="{ props }">
              <v-btn
                icon
                variant="plain"
                :to="{
                  name: 'events',
                }"
                size="medium"
                v-bind="props"
              >
                <v-icon color="lighterIcons">fas fa-envelope</v-icon>
              </v-btn>
            </template>
            {{ $t("labels.unread_messages") }}
          </v-tooltip>
        </v-badge>
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="align-self-center">
              <router-link :to="{ name: 'releases' }">
                <v-badge
                  color="warning"
                  dot
                  offset-x="5"
                  offset-y="25"
                  :model-value="displayNewReleaseBadge"
                >
                  <v-icon
                    class="mx-2 fs-20"
                    color="lighterIcons"
                    icon="fa fa-bullhorn"
                  ></v-icon>
                </v-badge>
              </router-link>
            </span>
          </template>
          {{ $t("releases") }}
        </v-tooltip>
        <v-tooltip location="bottom" v-if="impersonator">
          <template v-slot:activator="{ props }">
            <v-icon v-bind="props" class="mx-1 align-self-center" color="purple"
              >fas fa-mask</v-icon
            >
          </template>
          {{ $t("impersonated") }}
        </v-tooltip>
        <v-tooltip location="bottom" v-if="!emailVerified">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="align-self-center">
              <router-link :to="{ name: 'user-page' }">
                <v-icon class="mx-1" color="warning"
                  >fa fa-exclamation-triangle</v-icon
                >
              </router-link>
            </span>
          </template>
          {{ $t("email_not_verified") }}
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">
              <router-link :to="{ name: 'user-page' }">
                <v-avatar color="primary">
                  <img
                    v-if="loggedIn && user"
                    :src="gravatar"
                    :alt="avatarText"
                  />
                  <v-icon v-else dark>fas fa-user</v-icon>
                </v-avatar>
              </router-link>
            </span>
          </template>
          <span>{{ usernameText }}</span>
        </v-tooltip>
      </v-toolbar-items>
    </v-app-bar>
    <!-- we need some empty space at the bottom of each page for the
         floating info button to fit in -->
    <v-main
      v-if="selectedOrganizationId || !showOrganizationSelector"
      class="mb-8"
    >
      <v-alert
        v-if="displayNewReleaseAlert"
        class="ma-4 mt-6 alert_new_version"
        @input="dismissLastRelease(false)"
        density="compact"
        dismissible
        variant="outlined"
        closable
        icon="fa fa-bullhorn"
        close-icon="fa fa-times-circle"
        text
        type="success"
      >
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <span v-bind="props">
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
      <v-container fluid class="pa-0 pa-sm-2">
        <v-tooltip location="left" v-if="showHelpButton">
          <template #activator="{ props }">
            <v-btn
              color="info"
              size="small"
              position="fixed"
              location="bottom right"
              v-bind="props"
              target="_blank"
              :href="helpLink"
              class="fixed_button"
              rounded
            >
              {{ $t("knowledge_base") }}
              <v-icon size="small" class="ml-2">fa fa-truck-medical</v-icon>
            </v-btn>
          </template>
          {{ helpText || $t("context_help_tt") }}
        </v-tooltip>
        <router-view :key="$route.fullPath" v-if="loggedIn"></router-view>
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
    <LoginDialog></LoginDialog>
    <CreateOrganizationDialog
      v-if="showCreateOrganizationDialog"
    ></CreateOrganizationDialog>
  </v-app>
</template>

<script>
import SidePanel from "./SidePanel";
import { mapActions, mapGetters, mapState } from "vuex";
import OrganizationSelector from "@/components/selectors/OrganizationSelector";
import SelectedDateRangeWidget from "@/components/SelectedDateRangeWidget";
import LoginDialog from "@/components/account/LoginDialog";
import CreateOrganizationDialog from "@/components/account/CreateOrganizationDialog";
import axios from "axios";
import defaultLogo from "@/assets/celus-dark.png";
import md5 from "md5";
import defaultLogoHorizontal from "../assets/celus-horizontal-dark.svg";

import { useDisplay } from "vuetify";

export default {
  name: "Dashboard",
  components: {
    CreateOrganizationDialog,
    LoginDialog,
    SelectedDateRangeWidget,
    OrganizationSelector,
    SidePanel,
  },
  data() {
    return {
      navbarExpanded: false,
      showSidePanel: true,
      helpLink: false,
      helpText: "",
      defaultLogoHorizontal: defaultLogoHorizontal,
    };
  },
  setup() {
    const display = useDisplay();

    return { display };
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
      forceHideOrganizationSelector: "forceHideOrganizationSelector",
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
    hideOrganizationSelector() {
      return !!this.forceHideOrganizationSelector[this.$route.name];
    },
    hideDateRangeSelector() {
      return !!this.forceHideDateRangeSelector[this.$route.name];
    },
    showOrganizationSelector() {
      return (
        this.$vuetify.display.mdAndUp &&
        !this.$route.meta.hideOrganizationSelector &&
        !this.hideOrganizationSelector
      );
    },
    showDateRangeSelector() {
      return (
        this.$vuetify.display.mdAndUp &&
        !this.$route.meta.hideDateRangeSelector &&
        !this.hideDateRangeSelector
      );
    },
    showHelpButton() {
      return !!this.helpLink;
    },
    gravatar() {
      const hash = md5(this.user.email.trim().toLowerCase());
      return `https://www.gravatar.com/avatar/${hash}?d=mp&s=40`;
    },
  },

  methods: {
    ...mapActions({
      hideSnackbar: "hideSnackbar",
      dismissLastRelease: "dismissLastRelease",
    }),
    async fetchHelpLink() {
      try {
        const result = await axios.get(
          `https://spaces.celus.net/help/${this.$route.name}.json`,
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
      handler(to) {
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
  max-width: 128px;
  height: 36px;

  @media only screen and (max-width: 600px) {
    width: 20vw;
  }
}

.logo {
  max-width: 128px;
  height: 36px;

  @media only screen and (max-width: 600px) {
  }
}

.fixed_button {
  margin-right: 36px;
  margin-bottom: 16px;
  z-index: 4;
}
img.logo {
  max-width: 20vw;
}

img.logow {
  max-height: 92px;
}

.fs-30 {
  font-size: 30px;
  line-height: 30px;
}

.fs-20 {
  font-size: 20px;
  line-height: 28px;
}

.alert_new_version {
  background-color: rgb(76, 175, 80, 0.1);
}

:deep(.v-alert__close > button) {
  font-size: 15px;
}
</style>
