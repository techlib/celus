<template>
    <router-view
            v-if="$route.meta.outsideNormalLayout"
    >
    </router-view>

    <InvalidUserPage v-else-if="invalidUser" />

    <StandardLayout v-else-if="bootUpFinished" />

    <div v-else>
        <v-app>
            <BootUpWidget />
            <LoginDialog v-if="showLoginDialog" />
        </v-app>
    </div>

</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import InvalidUserPage from './InvalidUserPage'
  import StandardLayout from './StandardLayout'
  import BootUpWidget from '../components/BootUpWidget'
  import LoginDialog from '../components/account/LoginDialog'

  export default {
    name: 'Dashboard',
    components: {
      LoginDialog,
      BootUpWidget,
      InvalidUserPage,
      StandardLayout,
    },
    data () {
      return {
      }
    },
    computed: {
      ...mapState({
        invalidUser: 'invalidUser',
        user: 'user',
        showLoginDialog: 'showLoginDialog',
      }),
      ...mapGetters({
        loggedIn: 'loggedIn',
        bootUpFinished: 'bootUpFinished',
      }),
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
        start: 'start',
      }),
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

<style lang="scss">

    img.avatar {
        font-size: 1.25rem;
    }

    section.header {
        margin-bottom: 2rem;
    }

    div.fields {
        margin-top: 1rem;
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
