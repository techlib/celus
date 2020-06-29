<i18n lang="yaml">
en:
    is_superuser: Superuser
    is_from_master_organization: CzechELib staff
    associated_organizations: Associated organizations
    associated_organizations_note: Super users and CzechELib users have access to all available organizations, but only
                                   those listed below are explicitly associated with this account
    organization: Organization
    is_admin: Admin
    unverified_email: Your email address has not been verified. Some functions of Celus will not be available.
        Check your email for a verification message from Celus.
    resend_verification_email: Resend verification email
    verification_resent: Verification email was resent

cs:
    is_superuser: Superuživatel
    is_from_master_organization: Člen CzechELib týmu
    associated_organizations: Přiřazené organizace
    associated_organizations_note: Superuživatelé a členové CzechELib týmu mají přístup ke všem organizacím. Níže jsou
                                   uvedené jen ty, ke kterým je uživatel explicitně přiřazen.
    organization: Organizace
    is_admin: Administrátor
    unverified_email: Vaše emailová adresa nebyla ověřená. Některé funkce systému nebudou k dispozici.
        Zkontrolujte ověřovací email od aplikace Celus ve své schránce.
    resend_verification_email: Znovu zaslat ověřovací email
    verification_resent: Ověřovací email byl znovu zaslán
</i18n>

<template>
    <div v-if="loggedIn && user" class="text-center">
        <v-avatar color="primary" class="mt-10" size="80">
            <v-gravatar
                    :email="user.email"
                    :alt="avatarText"
                    default-img="mp"
            >
            </v-gravatar>
        </v-avatar>

        <h3 v-if="user.first_name || user.last_name" class="subdued mt-3">
            {{ user.first_name ? user.first_name : '' }} {{ user.last_name ? user.last_name : '' }}
        </h3>
        <h4 v-if="user.email" class="font-weight-light mb-1">{{ user.email }}</h4>

        <div class="py-2" v-if="canLogout">
            <v-btn @click="logout" v-text="$t('logout')"></v-btn>
        </div>


        <v-alert
                v-if="!emailVerified"
                type="warning"
                class="my-3 py-5"
                outlined
        >
            {{ $t('unverified_email') }}
            <v-btn
                    color="primary"
                    @click="resendVerificationEmail()"
                    class="my-5"
            >
                {{ $t('resend_verification_email') }}
            </v-btn>
        </v-alert>


        <div class="mb-10 font-weight-black">
            <span v-if="user.is_superuser" v-text="$t('is_superuser')"></span>
            <span v-else-if="user.is_from_master_organization" v-text="$t('is_from_master_organization')"></span>
        </div>

        <h2 v-text="$t('associated_organizations')"></h2>
        <div class="font-weight-light mt-2 mb-4" v-if="user.is_superuser || user.is_from_master_organization" v-text="'* ' + $t('associated_organizations_note')"></div>

        <v-data-table
                :items="organizationList"
                :headers="headers"
        >
            <template v-slot:item.is_admin="{item}">
                <CheckMark :value="item.is_admin" />
            </template>

        </v-data-table>

    </div>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import VGravatar from 'vue-gravatar'
  import CheckMark from '../components/CheckMark'
  import axios from 'axios'

  export default {
    name: "UserPage",
    components: {VGravatar, CheckMark},
    data () {
      return {

      }
    },
    computed: {
      ...mapState({
        organizations: 'organizations',
        user: 'user',
      }),
      ...mapGetters({
        loggedIn: 'loggedIn',
        avatarText: 'avatarText',
        usernameText: 'usernameText',
        canLogout: 'canLogout',
        emailVerified: 'emailVerified',
      }),
      headers () {
        return [
          {
            text: this.$t('organization'),
            value: 'name',
          },
           {
            text: this.$t('is_admin'),
            value: 'is_admin',
          },
        ]
      },
      organizationList () {
        return Object.values(this.organizations).filter(item => item.is_member)
      },
    },

    methods: {
      ...mapActions({
        logout: 'logout',
        loadUserData: 'loadUserData',
        showSnackbar: 'showSnackbar',
      }),
      async resendVerificationEmail () {
        try {
          await axios.post('/api/user/verify-email')
          this.showSnackbar({content: this.$t('verification_resent'), color: 'success'})
        } catch (error) {
          this.showSnackbar({content: 'Error sending verification email: '+error, color: 'error'})
        }
      }
    },

    mounted () {
      // redownload user data on page load to make it is up-to-date
      this.loadUserData()
    }
  }
</script>

<style scoped>

</style>
