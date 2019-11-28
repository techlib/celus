<i18n lang="yaml">
en:
    not_logged_in: Logged out
    not_logged_in_text: You are not logged in, probably because you have been logged out due to inactivity. Please click "Login" to be redirected to login page.
    login: Login

cs:
    not_logged_in: Jste odhlášeni
    not_logged_in_text: Pravděpodobně jste byli odhlášeni z důvodu neaktivity. Prosím stiskněte "Přihlásit" pro opětovné přihlášení.
    login: Přihlásit
</i18n>

<template>
    <v-dialog v-model="showLoginDialog" persistent max-width="290">
        <v-card>
            <v-card-title class="headline">{{ $t('not_logged_in') }}</v-card-title>
            <v-card-text>{{ $t('not_logged_in_text') }}</v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text :href="$route.path + '?t=' + currentTimestamp">{{ $t('login') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>
<script>
  export default {
    name: 'LoginDialog',
    props: {
      value: {},
    },
    computed: {
      showLoginDialog: {
        get () {
          return this.$store.state.showLoginDialog
        },
        set (newValue) {
          this.$store.dispatch('setShowLoginDialog', {show: newValue})
        }
      },
      currentTimestamp () {
        // we add the current timestamp param to the URL in order to unsure the
        // page will not be fetched from cache by the browser
        return new Date().getTime()
      }
    }
  }
</script>
<style lang="scss">

    .v-select.v-text-field.short input {
        max-width: 0;
    }

</style>
