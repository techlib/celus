<template>
    <v-app v-if="!invalidUser">
        <SidePanel />

        <v-app-bar app clipped-left>
            <v-toolbar-title>
                <img src="../assets/czechelib-stats-64.svg" alt="CzechELib stats">
            </v-toolbar-title>

            <v-divider
                    class="mx-3"
                    inset
                    vertical
            ></v-divider>

            <OrganizationSelector :lang="appLanguage" />
            <v-spacer></v-spacer>

            <SelectedDateRangeWidget />
            <v-spacer></v-spacer>

            <v-select
                    v-model="appLanguage"
                    :items="['cs','en']"
                    prepend-icon="fa-globe"
                    class="short"
                    shrink
            >
            </v-select>
            <v-toolbar-items class="hidden-sm-and-down">
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

        </v-app-bar>

        <v-content>
            <v-container fluid>

                <router-view/>

                <v-snackbar v-model="snackbarShow" :color="snackbarColor">
                    {{ snackbarText }}
                    <v-btn dark text @click="hideSnackbar">
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

  export default {
    name: 'Dashboard',
    components: {
      InvalidUserPage,
      LoginDialog,
      SelectedDateRangeWidget,
      OrganizationSelector,
      SidePanel,
    },
    data () {
      return {
        navbarExpanded: false,
      }
    },
    computed: {
      ...mapState({
        snackbarText: 'snackbarContent',
        snackbarColor: 'snackbarColor',
        invalidUser: 'invalidUser',
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
        console.info("Switching language to:", this.appLanguage)
        this.$i18n.locale = this.appLanguage
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

</style>
