<i18n>
en:
    email_not_verified: Your email is not verified

cs:
    email_not_verified: Vaše emailová adresa není ověřená
</i18n>

<template>
    <v-app>
        <SidePanel v-model="showSidePanel" />

        <v-app-bar app clipped-left>
            <v-toolbar-title class="flex-sm-shrink-0">
                <img
                        :src="siteLogo ? siteLogo.img : require('../assets/celus-plus-dark.svg')"
                        :alt="siteLogo ? siteLogo.alt_text : 'Celus'"
                        id="logo-image">
            </v-toolbar-title>

            <v-divider
                    class="mx-3 d-none d-md-block"
                    inset
                    vertical
            ></v-divider>

            <OrganizationSelector internal-label :lang="appLanguage" class="d-none d-md-flex" />
            <SelectedDateRangeWidget input-like-label class="d-none d-md-flex" />
            <v-spacer></v-spacer>

            <v-select
                    v-model="appLanguage"
                    :items="['cs','en']"
                    prepend-icon="fa-globe"
                    class="short"
                    shrink
            >
            </v-select>

            <!-- user icon -->
            <v-toolbar-items>
                <v-divider
                        class="mx-3"
                        inset
                        vertical
                ></v-divider>

                <v-tooltip bottom v-if="!emailVerified">
                    <template v-slot:activator="{ on }">
                        <span v-on="on">
                            <router-link :to="{name: 'user-page'}">
                                <v-icon class="mx-2 mt-5" color="warning">fa fa-exclamation-triangle</v-icon>
                            </router-link>
                        </span>
                    </template>
                    {{ $t('email_not_verified') }}
                </v-tooltip>

                <v-tooltip bottom>
                    <template v-slot:activator="{ on }">
                        <span v-on="on" >
                            <router-link :to="{name: 'user-page'}">
                                <v-avatar color="primary" class="mt-2">
                                    <v-gravatar
                                            v-if="loggedIn && user"
                                            :email="user.email"
                                            :alt="avatarText"
                                            default-img="mp"
                                    >
                                    </v-gravatar>
                                    <v-icon
                                            v-else
                                            dark
                                    >fa-user</v-icon>
                                </v-avatar>
                            </router-link>
                        </span>
                    </template>
                    <span>{{ usernameText }}</span>
                </v-tooltip>
            </v-toolbar-items>

            <v-btn
                    @click.stop="showSidePanel=!showSidePanel"
                    icon
                    class="d-md-hide">
                <v-icon>fa fa-bars</v-icon>
            </v-btn>
        </v-app-bar>

        <v-content>
            <v-container fluid pa-0 pa-sm-2>

                <IntroPage v-if="loggedIn && showIntro" />
                <router-view :key="$route.fullPath" v-else-if="loggedIn"/>

                <!--keep-alive max="5">
                    <router-view :key="$route.fullPath"/>
                </keep-alive-->

                <v-snackbar v-model="snackbarShow" :color="snackbarColor">
                    {{ snackbarText }}
                    <v-btn dark text @click="hideSnackbar">
                        Close
                    </v-btn>
                </v-snackbar>
            </v-container>
        </v-content>
        <v-footer app absolute inset height="128px" v-if="footerImages.length">
            <v-container fluid>
                <v-row no-gutters wrap>
                    <v-col cols="auto" v-for="(image, index) of footerImages" :key="index">
                        <img :src="image.img" :alt="image.alt_text" class="logow">
                    </v-col>
                </v-row>
            </v-container>
        </v-footer>

        <LoginDialog />
        <CreateOrganizationDialog />
    </v-app>
</template>

<script>
  import SidePanel from './SidePanel'
  import { mapActions, mapGetters, mapState } from 'vuex'
  import OrganizationSelector from '../components/OrganizationSelector'
  import SelectedDateRangeWidget from '../components/SelectedDateRangeWidget'
  import LoginDialog from '../components/account/LoginDialog'
  import InvalidUserPage from './InvalidUserPage'
  import VGravatar from 'vue-gravatar'
  import CreateOrganizationDialog from '../components/account/CreateOrganizationDialog'
  import IntroPage from './IntroPage'

  export default {
    name: 'Dashboard',
    components: {
      IntroPage,
      CreateOrganizationDialog,
      InvalidUserPage,
      LoginDialog,
      SelectedDateRangeWidget,
      OrganizationSelector,
      SidePanel,
      VGravatar,
    },
    data () {
      return {
        navbarExpanded: false,
        showSidePanel: true,
      }
    },
    computed: {
      ...mapState({
        snackbarText: 'snackbarContent',
        snackbarColor: 'snackbarColor',
        user: 'user',
        siteLogo: state => state.siteConfig.siteLogo,
        siteName: state => state.siteConfig.siteName,
        footerImages: state => state.siteConfig.footerImages,
      }),
      ...mapGetters({
        loggedIn: 'loggedIn',
        avatarText: 'avatarText',
        avatarImg: 'avatarImg',
        usernameText: 'usernameText',
        bootUpFinished: 'bootUpFinished',
        emailVerified: 'emailVerified',
        showIntro: 'showIntro',
      }),
      snackbarShow: {
        get () {
          return this.$store.state.snackbarShow
        },
        set (newValue) {
          if (newValue === false)
            this.hideSnackbar()
        }
      },
      appLanguage: {
        get () {
          return this.$store.state.appLanguage
        },
        async set (newValue) {
          await this.$store.dispatch('setAppLanguage', {lang: newValue})
          this.$router.go()
        }
      },
    },
    methods: {
      ...mapActions({
        hideSnackbar: 'hideSnackbar',
        start: 'start',
      }),
      toggleNavbar () {
        this.navbarExpanded = !this.navbarExpanded
      },
    },
    created() {
      this.start()
    },
    async mounted () {
      this.$i18n.locale = this.appLanguage
    },
    watch: {
      appLanguage () {
        this.$i18n.locale = this.appLanguage
      },
    }

  }
</script>

<style lang="scss" scoped>

    #logo-image {
        @media only screen and (max-width:600px) {
            width: 20vw;
        }
        max-width: 128px;
    }

    img.logo {
        max-width: 20vw;
    }

    img.logow {
        max-height: 92px;
    }

</style>
