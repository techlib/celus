<i18n lang="yaml" src="@/locales/dialog.yaml" />

<i18n>
en:
    email_not_verified: Your email is not verified
    impersonated: You are currently impersonating another user.
    no_help: No help available for this page
    help_panel_tt: Context specific help

cs:
    email_not_verified: Vaše emailová adresa není ověřená
    impersonated: Právě se zosobňujete jiného uživatele.
    no_help: Pro tuto stránku není dostupná žádná nápověda
    help_panel_tt: Nápověda pro aktuální stránku
</i18n>

<template>
  <v-app>
    <SidePanel
      v-model="showSidePanel"
      data-tour="side-panel"
      :tour-name="offeredTour"
    />

    <v-navigation-drawer right app v-model="showHelpPanel" clipped>
      <div class="pa-3">
        <router-view name="helpPanel" />
      </div>
    </v-navigation-drawer>

    <v-app-bar app clipped-left clipped-right data-tour="app-bar">
      <v-toolbar-title class="flex-sm-shrink-0">
        <img
          :src="
            siteLogo ? siteLogo.img : require('../assets/celus-plus-dark.svg')
          "
          :alt="siteLogo ? siteLogo.alt_text : 'Celus'"
          id="logo-image"
        />
      </v-toolbar-title>

      <v-divider class="mx-3 d-none d-md-block" inset vertical></v-divider>

      <OrganizationSelector
        internal-label
        :lang="appLanguage"
        v-if="showOrganizationSelector"
        class="d-flex"
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
        prepend-icon="fa-globe"
        class="short"
        shrink
      >
      </v-select>

      <!-- user icon -->
      <v-toolbar-items>
        <v-divider class="mx-3" inset vertical></v-divider>

        <v-tooltip bottom v-if="impersonator">
          <template v-slot:activator="{ on }">
            <v-icon v-on="on" class="mr-2" color="purple">fa-mask</v-icon>
          </template>
          {{ $t("impersonated") }}
        </v-tooltip>
        <v-tooltip bottom v-if="!emailVerified">
          <template v-slot:activator="{ on }">
            <span v-on="on">
              <router-link :to="{ name: 'user-page' }">
                <v-icon class="mx-2 mt-5" color="warning"
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
                <v-avatar color="primary" class="mt-2" data-tour="user-avatar">
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
        data-tour="menu-show-button"
      >
        <v-icon>fa fa-bars</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
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
              @click="helpPanelOpen = !helpPanelOpen"
            >
              <v-icon
                >{{ helpPanelOpen ? "fa-angle-right" : "fa-question" }}
              </v-icon>
            </v-btn>
          </template>
          {{ $t("help_panel_tt") }}
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

    <UITour name="basic" />
  </v-app>
</template>

<script>
import SidePanel from "./SidePanel";
import { mapActions, mapGetters, mapState } from "vuex";
import OrganizationSelector from "@/components/OrganizationSelector";
import SelectedDateRangeWidget from "@/components/SelectedDateRangeWidget";
import LoginDialog from "@/components/account/LoginDialog";
import VGravatar from "vue-gravatar";
import CreateOrganizationDialog from "@/components/account/CreateOrganizationDialog";
import UITour from "@/components/help/UITour";

export default {
  name: "Dashboard",
  components: {
    UITour,
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
      basicsTourName: "basic",
      helpPanelOpen: false,
    };
  },
  computed: {
    ...mapState({
      snackbarText: "snackbarContent",
      snackbarColor: "snackbarColor",
      user: "user",
      siteLogo: (state) => state.siteConfig.siteLogo,
      siteName: (state) => state.siteConfig.siteName,
      footerImages: (state) => state.siteConfig.footerImages,
    }),
    ...mapGetters({
      loggedIn: "loggedIn",
      avatarText: "avatarText",
      avatarImg: "avatarImg",
      usernameText: "usernameText",
      bootUpFinished: "bootUpFinished",
      emailVerified: "emailVerified",
      impersonator: "impersonator",
      tourFinished: "tourFinished",
      tourNeverSeen: "tourNeverSeen",
      showCreateOrganizationDialog: "showCreateOrganizationDialog",
      activeLanguageCodes: "activeLanguageCodes",
    }),
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
    userBasicTourFinished() {
      return this.tourFinished(this.basicsTourName);
    },
    showLanguageSelector() {
      return this.activeLanguageCodes.length > 1;
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
        !this.$route.meta.hideOrganizationSelector
      );
    },
    canShowBasicTour() {
      // the tour requires date range and organization selectors to be visible
      return this.showOrganizationSelector && this.showDateRangeSelector;
    },
    offeredTour() {
      // it should only be offered in the side bar when it has already been
      // finished by the user
      if (this.canShowBasicTour && this.userBasicTourFinished) {
        return "basic";
      }
      return null;
    },
    showHelpButton() {
      return !!this.$route.matched[0].components.helpPanel;
    },
    showHelpPanel: {
      get() {
        return this.showHelpButton && this.helpPanelOpen;
      },
      set(value) {
        this.helpPanelOpen = value;
      },
    },
  },

  methods: {
    ...mapActions({
      hideSnackbar: "hideSnackbar",
      start: "start",
      backstageChangeTourStatus: "backstageChangeTourStatus",
    }),
    toggleNavbar() {
      this.navbarExpanded = !this.navbarExpanded;
    },
  },

  created() {
    this.start();
  },

  async mounted() {
    this.$i18n.locale = this.appLanguage;
    if (
      !this.userBasicTourFinished &&
      !this.showCreateOrganizationDialog &&
      this.canShowBasicTour
    ) {
      this.$tours[this.basicsTourName].start();
    }
  },

  watch: {
    appLanguage() {
      this.$i18n.locale = this.appLanguage;
    },

    userBasicTourFinished() {
      if (!this.userBasicTourFinished && this.canShowBasicTour) {
        this.$tours[this.basicsTourName].start();
      }
    },

    showCreateOrganizationDialog() {
      if (!this.showCreateOrganizationDialog && !this.userBasicTourFinished) {
        this.$tours[this.basicsTourName].start();
      }
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

.v-navigation-drawer {
  &.v-tour__target--relative {
    position: fixed;
  }
}
</style>
