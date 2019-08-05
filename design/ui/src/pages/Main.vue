<template>
    <v-app>
        <SidePanel />

        <v-toolbar app clipped-left>
            <!--v-toolbar-side-icon></v-toolbar-side-icon-->
            <v-toolbar-title>
                <img src="../assets/czechelib-stats-64.svg" alt="CzechELib stats">
            </v-toolbar-title>

            <v-divider
                    class="mx-3"
                    inset
                    vertical
            ></v-divider>

            <OrganizationSelector :lang="appLang" />
            <v-spacer></v-spacer>

            <SelectedDateRangeWidget />
            <v-spacer></v-spacer>

            <v-toolbar-items class="hidden-sm-and-down">
                <v-select
                        v-model="appLang"
                        :items="['cs','en']"
                        prepend-icon="fa-globe"
                        class="short"
                >
                </v-select>
                <v-divider
                        class="mx-3"
                        inset
                        vertical
                ></v-divider>
                <v-avatar size="36px" color="primary" class="mt-2">
                    <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                        <span v-on="on" >
                            <img
                                    v-if="avatarImg"
                                    src="https://avatars0.githubusercontent.com/u/9064066?v=4&s=460"
                                    alt="Avatar"
                            >
                            <span v-else-if="loggedIn" class="white--text headline">{{ avatarText }}</span>
                            <v-icon
                                    v-else
                                    dark
                            >fa-user</v-icon>
                        </span>
                        </template>

                        <span>{{ usernameText }}</span>
                    </v-tooltip>
                </v-avatar>
            </v-toolbar-items>

        </v-toolbar>

        <v-content>
            <v-container fluid>

                <router-view/>

                <v-snackbar v-model="snackbarShow">
                    {{ snackbarText }}
                    <v-btn dark flat @click="hideSnackbar">
                        Close
                    </v-btn>
                </v-snackbar>
            </v-container>
        </v-content>
        <v-footer app absolute inset height="128px">
            <v-layout>
                <v-flex>
                    <img src="../assets/eu_fond.svg" alt="Logo ESI fondu" >
                </v-flex>
                <v-flex>
                    <img src="../assets/MSMT_cz.svg" alt="Logo MŠMT" >
                </v-flex>
                <v-flex>
                    <img src="../assets/ntk-96.svg" alt="Logo NTK" >
                </v-flex>
            </v-layout>
        </v-footer>

        <v-layout justify-center>
            <v-dialog v-model="showLoginDialog" persistent max-width="290">
                <v-card>
                    <v-card-title class="headline">Not logged in</v-card-title>
                    <v-card-text>You are not logged in. Please click Login to be redirected to login page.</v-card-text>
                    <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn color="primary" text href="/secure">Login</v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>
        </v-layout>
    </v-app>
</template>

<script>
  import SidePanel from './SidePanel'
  //import LoginDialog from '../components/LoginDialog'
  import { mapActions, mapGetters, mapState } from 'vuex'
  import OrganizationSelector from '../components/OrganizationSelector'
  import SelectedDateRangeWidget from '../components/SelectedDateRangeWidget'

  export default {
    name: 'Dashboard',
    components: {
      SelectedDateRangeWidget,
      OrganizationSelector,
      SidePanel,
      //LoginDialog
    },
    data () {
      return {
        navbarExpanded: false,
        appLang: 'cs',
      }
    },
    computed: {
      ...mapState({
        snackbarText: 'snackbarContent',
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
      showLoginDialog: {
        get () {
          return this.$store.state.showLoginDialog
        },
        set (newValue) {
          this.$store.dispatch('setShowLoginDialog', {show: newValue})
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
    created () {
      this.start()
    },
    watch: {
      appLang () {
        this.$i18n.locale = this.appLang
      },
    }

  }
</script>

<style lang="scss">

    .v-select.v-text-field.short input {
        max-width: 0;
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

</style>
