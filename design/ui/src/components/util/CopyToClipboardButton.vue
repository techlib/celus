<i18n lang="yaml">
en:
  copied: Copied to clipboard
  copy_failed: Failed to copy

cs:
  copied: Zkopírováno do schránky
  copy_failed: Nepodařilo se zkopírovat
</i18n>

<template>
  <v-btn
    icon="fa fa-copy"
    size="small"
    variant="text"
    color="grey"
    :loading="copying"
    @click="copyToClipboard"
  />
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "CopyToClipboardButton",

  props: {
    value: {
      type: String,
      required: true,
    },
  },

  data() {
    return {
      copying: false,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async copyToClipboard() {
      this.copying = true;
      try {
        await navigator.clipboard.writeText(this.value);
        this.showSnackbar({
          content: this.$t("copied"),
          color: "success",
        });
      } catch (error) {
        console.error("Failed to copy to clipboard:", error);
        this.showSnackbar({
          content: this.$t("copy_failed"),
          color: "error",
        });
      } finally {
        this.copying = false;
      }
    },
  },
};
</script>
