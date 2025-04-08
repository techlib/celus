import validateEmail from "@/libs/email-validation";

export default {
  data() {
    const minPasswordLength = 8;
    return {
      minPasswordLength,
      rules: {
        required: (value) => !!value || this.$t("required"),
        min: (v) => v.length >= minPasswordLength || this.$t("min_pwd_length"),
        email: (v) => !!validateEmail(v) || this.$t("email_required"),
        atLeastOne: (v) => (v && v.length > 0) || this.$t("required"),
      },
    };
  },
};
