<template>
  <div>
    <v-container v-if="showIntroVideo">
      <v-row>
        <v-col cols="12" lg="10" xl="6" offset-lg="1" offset-xl="3">
          <h2>Add your first SUSHI credentials</h2>
        </v-col>
      </v-row>
      <v-row justify="center">
        <v-col cols="12">
          <IntroVideo class="mx-auto"></IntroVideo>
        </v-col>
      </v-row>
      <v-row justify="center">
        <v-col class="text-center" cols="12" lg="9" xl="6">
          CELUS needs some data to work with. Check the above video or our
          <a
            target="_blank"
            href="https://support.celus.net/support/solutions/articles/103000078036"
            >knowledgebase article</a
          >
          to learn how to add your first SUSHI credentials. Or simply click the
          button below to get started.
        </v-col>
      </v-row>
      <v-row>
        <v-col class="text-center pt-12">
          <v-btn
            @click="showCreateDialog = true"
            color="primary"
            size="x-large"
          >
            <v-icon class="pe-2" size="small">fa-plus</v-icon>
            Add SUSHI credentials
          </v-btn>
        </v-col>
      </v-row>
      <v-row justify="center">
        <v-col class="text-center pt-12" cols="12" lg="9" xl="6">
          <em>Tip:</em>
          If you have a lot of credentials, you can email them to us and we will
          load them for you. <br />Just
          <a :href="exportForImportUrl">download this template</a>, fill it in,
          and send it to
          <a
            :href="`mailto:${contactEmail}?subject=${subjectForImportCredEmail}`"
            >{{ contactEmail }}</a
          >.
        </v-col>
      </v-row>
    </v-container>
    <SushiCredentialsManagementWidget
      v-else
      :organization-id="organizationId"
      :potential-issues="brokenOnly ? 'broken' : null"
      show-platform-filter
      ref="sushiCredentialsWidget"
    ></SushiCredentialsManagementWidget>
    <v-dialog
      v-model="showCreateDialog"
      v-if="showCreateDialog"
      :max-width="dialogMaxWidth"
    >
      <SushiCredentialsEditDialog
        v-model="showCreateDialog"
        @update-credentials="updateCredentials"
      ></SushiCredentialsEditDialog>
    </v-dialog>
  </div>
</template>

<script>
import SushiCredentialsManagementWidget from "@/components/sushi/SushiCredentialsManagementWidget";
import { mapActions, mapGetters, mapState } from "vuex";
import SushiCredentialsEditDialog from "@/components/sushi/SushiCredentialsEditDialog.vue";
import IntroVideo from "@/components/sushi/IntroVideo.vue";

export default {
  name: "SushiCredentialsManagementPage",

  components: {
    IntroVideo,
    SushiCredentialsEditDialog,
    SushiCredentialsManagementWidget,
  },

  data() {
    return {
      showCreateDialog: false,
      dialogMaxWidth: 1024,
      intro: "intro" in this.$route.query,
    };
  },

  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      showIntro: "showIntro",
      contactEmail: "contactEmail",
      subjectForImportCredEmail: "subjectForImportCredEmail",
    }),
    brokenOnly() {
      return "broken" in this.$route.query;
    },
    exportForImportUrl() {
      return `/api/sushi-credentials/import-template/?organization=${this.organizationId}`;
    },
    showIntroVideo() {
      return this.showIntro || this.intro;
    },
  },

  methods: {
    ...mapActions(["loadSushiCredentialsCount"]),
    updateCredentials() {
      this.loadSushiCredentialsCount();
      this.intro = false;
    },
  },

  watch: {
    showCreateDialog() {
      if (!this.showCreateDialog) {
        if (this.$refs.sushiCredentialsWidget) {
          this.$refs.sushiCredentialsWidget.loadSushiCredentialsList();
        }
      }
    },
  },
};
</script>

<style lang="scss">
iframe {
  border: none;
}
</style>
