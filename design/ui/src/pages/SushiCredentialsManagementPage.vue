<template>
  <SushiCredentialsManagementWidget
    :organization-id="organizationId"
    :show-broken-only="brokenOnly"
  />
</template>

<script>
import SushiCredentialsManagementWidget from "@/components/sushi/SushiCredentialsManagementWidget";
import { mapState } from "vuex";

export default {
  name: "SushiCredentialsManagementPage",

  components: {
    SushiCredentialsManagementWidget,
  },

  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    brokenOnly() {
      return "broken" in this.$route.query;
    },
  },
};
</script>

<style lang="scss"></style>
