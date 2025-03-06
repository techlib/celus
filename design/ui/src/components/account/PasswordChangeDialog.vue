<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  password_change: Password change
  new_password: New password
  change_success: Password was successfully changed
  change_password: Change password

cs:
  password_change: Změna hesla
  new_password: Nové heslo
  change_success: Heslo bylo úspěšně změněno
  change_password: Změnit heslo
</i18n>

<template>
  <v-dialog v-model="show" max-width="400px">
    <v-form ref="form" @submit.prevent="doChange()" :model-value="valid">
      <v-card>
        <v-card-title class="headline">{{
          $t("password_change")
        }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="password"
            :label="$t('new_password')"
            :rules="[error, rules.required, rules.min]"
            :type="showPassword ? 'text' : 'password'"
            counter
          >
            <template #append-inner>
              <v-icon
                v-if="showPassword"
                @click="showPassword = !showPassword"
                size="x-small"
                icon="fa fa-eye"
              ></v-icon>
              <v-icon
                v-else
                @click="showPassword = !showPassword"
                size="x-small"
                icon="fa fa-eye-slash"
              ></v-icon>
            </template>
          </v-text-field>
        </v-card-text>
        <v-card-actions class="pa-6">
          <v-spacer></v-spacer>
          <v-btn
            @click="show = false"
            variant="flat"
            elevation="2"
            color="defaultButton"
            >{{ $t("cancel") }}
          </v-btn>
          <v-btn
            color="primary"
            :disabled="!valid || requestInProgress"
            type="submit"
            variant="flat"
            elevation="2"
          >
            {{ $t("change_password") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<script>
import { mapActions } from "vuex";
import formRulesMixin from "@/mixins/formRulesMixin";

export default {
  name: "PasswordChangeDialog",

  mixins: [formRulesMixin],

  props: {
    modelValue: {},
  },

  data() {
    return {
      password: "",
      showPassword: false,
      passwordEdited: false,
      requestInProgress: false, // if a request was just sent to the backend and is processed
      changeError: null,
      show: this.modelValue,
    };
  },

  computed: {
    valid() {
      return this.password.length >= 8;
    },
    error() {
      if (this.changeError && !this.passwordEdited) {
        if (
          this.changeError.response.data &&
          this.changeError.response.data.new_password2
        ) {
          return this.changeError.response.data.new_password2[0];
        }
      }
      return true;
    },
  },

  methods: {
    ...mapActions({
      login: "login",
      signup: "signup",
      changePassword: "changePassword",
      showSnackbar: "showSnackbar",
    }),
    resetForm() {
      this.password = "";
      this.showPassword = false;
      this.passwordEdited = false;
      this.requestInProgress = false;
      if (this.$refs.form) {
        // on first access, the form is not yet rendered
        this.$refs.form.resetValidation();
      }
    },
    async doChange() {
      this.requestInProgress = true;
      this.passwordEdited = false;
      this.changeError = null;
      try {
        await this.changePassword({ password: this.password });
        this.showSnackbar({
          content: this.$t("change_success"),
          color: "success",
        });
        this.$emit("update:modelValue", false);
      } catch (error) {
        this.changeError = error;
      } finally {
        this.requestInProgress = false;
      }
    },
  },

  watch: {
    password() {
      this.passwordEdited = true;
    },

    show() {
      this.$emit("update:modelValue", this.show);
      if (this.show) {
        this.resetForm();
      }
    },

    modelValue() {
      this.show = this.modelValue;
    },
  },
};
</script>

<style lang="scss">
.v-select.v-text-field.short input {
  max-width: 0;
}

div.small {
  font-size: 80%;
}
</style>
