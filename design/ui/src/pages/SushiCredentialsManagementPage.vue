<template>
  <SushiCredentialsManagementWidget :organization-id="organizationId" />
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
  },
};
</script>

<style lang="scss"></style>
