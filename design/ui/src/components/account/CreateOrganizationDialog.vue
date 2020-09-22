<i18n lang="yaml">
en:
  create_organization: Create your organization
  info_text: To start using Celus, you need to add your organization first. Just a name is enough for now.
  do_create: Create organization
  name: Name

cs:
  create_organization: Vytvořte svou organizaci
  info_text: K využívání Celusu je potřeba vytvořit svou organizaci. Prozatím postačí její název.
  do_create: Vytvořit organizaci
  name: Název
</i18n>

<template>
  <v-dialog v-model="showCreateOrganizationDialog" persistent max-width="600">
    <v-card>
      <v-card-title class="headline">{{
        $t("create_organization")
      }}</v-card-title>
      <v-card-text>
        <div>{{ $t("info_text") }}</div>
        <v-divider class="my-3"></v-divider>

        <v-form :value="valid">
          <v-text-field
            v-model="name"
            :label="$t('name') + '*'"
            aria-required="true"
          ></v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          @click="createOrganization"
          :disabled="!valid"
          class="ma-4"
          >{{ $t("do_create") }}</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
import axios from "axios";

export default {
  name: "CreateOrganizationDialog",

  data() {
    return {
      name: "",
    };
  },

  computed: {
    ...mapGetters({
      showCreateOrganizationDialog: "showCreateOrganizationDialog",
    }),
    valid() {
      return this.name !== "";
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      setOrganizations: "setOrganizations",
      selectFirstOrganization: "selectFirstOrganization",
      loadOrganizations: "loadOrganizations",
    }),
    async createOrganization() {
      try {
        await axios.post(
          "/api/organization/create-user-default/",
          { name: this.name },
          { privileged: true }
        );
        // we use the vuex defined action to load the organizations because it also does some
        // other magic, like updating the internal organization list, etc.
        await this.loadOrganizations();
      } catch (error) {
        this.showSnackbar({
          content: "Error creating organization: " + error,
          color: "error",
        });
      }
    },
  },
};
</script>

<style scoped></style>
