<template>
    <v-app v-if="!invalidUser">
        <SidePanel v-model="showSidePanel" />

        <v-app-bar app clipped-left>
            <v-toolbar-title>
                <img src="../assets/czechelib-stats-64.svg" alt="CzechELib stats">
            </v-toolbar-title>

            <v-divider
                    class="mx-3 d-none d-md-block"
                    inset
                    vertical
            ></v-divider>

            <OrganizationSelector :lang="appLanguage" class="d-none d-md-flex" />
            <v-spacer></v-spacer>

            <SelectedDateRangeWidget class="d-none d-md-flex" />
            <v-spacer></v-spacer>

            <v-select
                    v-model="appLanguage"
                    :items="['cs','en']"
                    prepend-icon="fa-globe"
                    class="short d-none d-md-flex"
                    shrink
            >
            </v-select>
            <v-toolbar-items class="hidden-sm-and-down">
                <v-divider
                        class="mx-3"
                        inset
                        vertical
                ></v-divider>

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

                <router-view :key="$route.fullPath"/>
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
        <v-footer app absolute inset height="128px">
            <v-container fluid>
                <v-row no-gutters wrap>
                <v-col cols="auto">
                    <img src="../assets/eu_fond.svg" alt="Logo ESI fondu" class="logow">
                </v-col>
                <v-col cols="auto">
                    <img src="../assets/MSMT_cz.svg" alt="Logo MŠMT" class="logow">
                </v-col>
                <v-col cols="auto">
                    <img src="../assets/ntk-96.svg" alt="Logo NTK" class="logow">
                </v-col>
                </v-row>
            </v-container>
        </v-footer>

        <v-layout justify-center>
            <LoginDialog />
        </v-layout>
    </v-app>
    <!-- invalid user state -->
    <InvalidUserPage v-else />
</template>

<script>
  import SidePanel from './SidePanel'
  import { mapActions, mapGetters, mapState } from 'vuex'
  import OrganizationSelector from '../components/OrganizationSelector'
  import SelectedDateRangeWidget from '../components/SelectedDateRangeWidget'
  import LoginDialog from '../components/LoginDialog'
  import InvalidUserPage from './InvalidUserPage'
  import VGravatar from 'vue-gravatar'

  export default {
    name: 'Dashboard',
    components: {
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
        invalidUser: 'invalidUser',
        user: 'user',
      }),
      ...mapGetters({
        loggedIn: 'loggedIn',
        avatarText: 'avatarText',
        avatarImg: 'avatarImg',
        usernameText: 'usernameText',
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
        set (newValue) {
          this.$store.dispatch('setAppLanguage', {lang: newValue})
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
    mounted () {
      this.start()
      this.$i18n.locale = this.appLanguage
    },
    watch: {
      appLanguage () {
        this.$i18n.locale = this.appLanguage
      },
    }

  }
</script>

<style lang="scss">

    .v-select.v-text-field.short input {
        max-width: 0;
        min-width: 3rem;
    }

    img.avatar {
        font-size: 1.25rem;
    }

    section.header {
        margin-bottom: 2rem;
    }

    div.fields {
        margin-top: 1rem;
    }

    footer.v-footer {
        // bottom: -100px;
    }

    div.v-input {

        &.short {
            flex-grow: 0;
        }

        div.v-input__control {
            div.v-text-field__details {
                min-height: 1px;
                .v-messages {
                    min-height: 1px;
                }
            }
        }
    }

    img.logo {
        max-width: 20vw;
    }

    img.logow {
        max-height: 10vw;
    }

</style>
