import validateEmail from "@/libs/email-validation";

export default {
  data() {
    return {
      rules: {
        required: (value) => !!value || this.$t("required"),
        min: (v) => v.length >= 8 || this.$t("min_pwd_length"),
        email: (v) => !!validateEmail(v) || this.$t("email_required"),
      },
    };
  },
};
