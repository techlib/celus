<template>
  <v-app v-if="newCelusVersion">
    <NewCelusVersionDialog />
  </v-app>

  <router-view v-else-if="$route.meta.outsideNormalLayout"> </router-view>

  <InvalidUserPage v-else-if="invalidUser" />

  <EmailNotVerified
    v-else-if="
      user &&
      !user.impersonator &&
      !emailVerified &&
      (!user.is_superuser || otpRequired)
    "
  />
  <StandardLayout v-else-if="bootUpFinished" />

  <div v-else>
    <v-app>
      <BootUpWidget />
      <LoginDialog v-if="showLoginDialog" />
      <OtpDialog v-else-if="otpRequired" />
    </v-app>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import InvalidUserPage from "./InvalidUserPage";
import EmailNotVerified from "./EmailNotVerified";
import StandardLayout from "./StandardLayout";
import BootUpWidget from "@/components/BootUpWidget";
import LoginDialog from "@/components/account/LoginDialog";
import OtpDialog from "@/components/account/OtpDialog";
import NewCelusVersionDialog from "@/components/NewCelusVersionDialog";

export default {
  name: "Dashboard",
  components: {
    LoginDialog,
    OtpDialog,
    BootUpWidget,
    InvalidUserPage,
    NewCelusVersionDialog,
    StandardLayout,
    EmailNotVerified,
  },
  data() {
    return {};
  },
  computed: {
    ...mapState({
      invalidUser: "invalidUser",
      user: "user",
      showLoginDialog: "showLoginDialog",
      otpRequired: "otpRequired",
      newCelusVersion: "newCelusVersion",
    }),
    ...mapGetters({
      loggedIn: "loggedIn",
      bootUpFinished: "bootUpFinished",
      emailVerified: "emailVerified",
    }),
    appLanguage: {
      get() {
        return this.$store.state.appLanguage;
      },
      set(newValue) {
        this.$store.dispatch("setAppLanguage", { lang: newValue });
        this.$router.go();
      },
    },
  },
  methods: {
    ...mapActions({
      start: "start",
    }),
  },
  created() {
    this.start();
  },
  async mounted() {
    this.$i18n.locale = this.appLanguage;
  },
  watch: {
    appLanguage() {
      this.$i18n.locale = this.appLanguage;
    },
  },
};
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

.subdued {
  color: #888888;
}

.top-dialog {
  position: absolute !important;
  top: 0 !important;

  @media screen and (min-height: 720px) {
    top: 10vh !important;
  }
}

table.overview-card {
  padding: 1rem;

  tr.header {
    th {
      font-variant: small-caps;
      font-weight: 500;
      font-size: 82.5%;
      border-bottom: solid 1px #dddddd;
      padding-top: 0.5rem;
    }
    &:first-child {
      th {
        padding-top: 0;
      }
    }
  }

  th {
    text-align: left;
    padding-right: 1.5rem;
    font-weight: 300;

    &.subdued-th {
      //font-weight: normal;
      color: #999999;
    }
  }
}

table.overview {
  th {
    text-align: left;
    padding-right: 1.5rem;
  }

  &.full-width {
    width: 100%;
  }
}

/* data and time formatting */
span.time {
  font-weight: 300;
  font-size: 87.5%;
}

ul.no-bullets {
  list-style: none;
  padding-left: 0;
}

.markdown {
  h3 {
    margin-bottom: 0.5rem;
  }
  h4 {
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
  }
}

.chart-value {
  font-weight: bold;
  color: #555555;
  text-align: right;
  padding-left: 1rem;
}

.chart-missing-data {
  color: #ff6633;
}

#date-range-selector {
  transition:
    background-color 0.2s,
    border 0.2s;
  border: solid 4px transparent;
  border-radius: 6px;
}

ul.unobtrusive-bullets {
  list-style-type: square;
  padding: 0 0 0 1rem;
  margin: 0;
}

th.align-top {
  vertical-align: top;
}

td.auto-width,
th.auto-width {
  width: auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.auto-table .v-data-table__wrapper table {
  th:last-child,
  td:last-child {
    width: 100%;
  }

  th:not(:last-child),
  td:not(:last-child) {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 6rem;
  }

  th.text-right {
    // only tds in right aligned columns should be right aligned, not the ths
    text-align: left !important;
  }
}

.v-tab {
  text-transform: uppercase;
}
</style>
