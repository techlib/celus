<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  confirm_delete:
    title: Delete confirmation
    records: Do you really want to delete following records?
    no_data: No data to delete.
    delete_ok: Selected data were deleted.
    title_reharvest: Delete before reharvest
    records_reharvest: Do you really want to continue reharvesting by deleting following records?
    delete_btn_reharvest: Delete & reharvest
cs:
  confirm_delete:
    title: Potvrzení smazání
    records: Opravdu si přejete smazat následující záznamy?
    no_data: Žádná data ke mazání.
    delete_ok: Vybraná data byla smazána.
    title_reharvest: Smazat před reharvestem
    records_reharvest: Opravdu si přejete pokračovat v reharvestu smazáním následujících záznamů?
    delete_btn_reharvest: Smazat a reharvestovat
</i18n>

<template>
  <v-card>
    <v-card-title class="headline">
      {{
        reharvest
          ? $t("confirm_delete.title_reharvest")
          : $t("confirm_delete.title")
      }}
    </v-card-title>
    <v-card-text>
      <ImportBatchesList
        v-model="importBatches"
        v-if="importBatches && (loading || canDelete)"
        :import-batches="importBatches"
        :title-text="
          reharvest
            ? $t('confirm_delete.records_reharvest')
            : $t('confirm_delete.records')
        "
        :loading="loading"
      />
      <p v-else>{{ $t("confirm_delete.no_data") }}</p>
    </v-card-text>
    <v-card-actions>
      <v-btn
        color="error"
        class="ma-3"
        :loading="deleting"
        @click="deleteAll()"
        :disabled="!canDelete"
      >
        <v-progress-circular
          small
          indeterminate
          v-if="deleting"
          color="error"
          class="mr-2"
        />
        <v-icon v-else small class="pr-2">fas fa-trash</v-icon>

        {{
          reharvest
            ? $t("confirm_delete.delete_btn_reharvest")
            : $t("actions.delete")
        }}
      </v-btn>
      <v-spacer />
      <v-btn @click="cancelDialog()" class="mr-2">
        <v-icon small class="mr-1">fa fa-times</v-icon>
        {{ $t("actions.cancel") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import ImportBatchesList from "@/components/ImportBatchesList";

export default {
  name: "ImportBatchesDeleteConfirm",
  components: {
    ImportBatchesList,
  },
  props: {
    // These are the slices which are used to query import batches
    // to be deleted - will be displayed in UI and user has to
    // confirm the deletion
    importBatchSlices: { required: true, type: Array },

    // These slices are used to delete information regarding sushi downloads
    // (can be empty - in this case no downloads are deleted)
    //
    // Note that these records are deleted based on time / organization / platform
    // and not based on existing data and no confirmation is displayed here.
    intentionSlices: { required: false, type: Array, default: () => [] },
    // when used for deleting data during reharvest, we use different texts
    reharvest: { type: Boolean, default: false },
  },
  data() {
    return {
      loading: false,
      deleting: false,
      importBatches: [],
    };
  },

  computed: {
    deleteImportBatchesUrl() {
      return "/api/import-batch/purge/";
    },
    deleteIntentionsUrl() {
      return "/api/scheduler/intention/purge/";
    },
    lookupUrl() {
      return "/api/import-batch/lookup/?order_by=pk";
    },
    importBatchesKeys() {
      return this.importBatches.map((e) => e.pk);
    },
    canDelete() {
      return this.importBatchesKeys.length > 0;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadImportBatches() {
      this.loading = true;
      try {
        let response = await axios.post(this.lookupUrl, this.importBatchSlices);
        this.importBatches = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading importBatches: " + error,
        });
      } finally {
        this.loading = false;
      }
    },
    async deleteAll() {
      this.deleting = true;
      await this.deleteImportBatches();
      await this.deleteIntentions();
      this.$emit("deleted");
      this.deleting = false;
    },
    async deleteImportBatches() {
      try {
        await axios.post(this.deleteImportBatchesUrl, {
          batches: this.importBatchesKeys,
        });
        this.showSnackbar({
          content: this.$t("confirm_delete.delete_ok"),
          color: "success",
        });
      } catch (error) {
        this.showSnackbar({
          content: "Error deleting import batches: " + error,
        });
      }
    },
    async deleteIntentions() {
      if (this.intentionSlices.length === 0) {
        return;
      }
      try {
        await axios.post(this.deleteIntentionsUrl, this.intentionSlices);
      } catch (error) {
        this.showSnackbar({
          content: "Error deleting intentions: " + error,
        });
      }
    },
    cancelDialog() {
      this.importBatches = [];
      this.$emit("cancel");
    },
  },

  mounted() {
    this.loadImportBatches();
  },
};
</script>
