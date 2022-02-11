<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  confirm_delete:
    title: Delete confirmation
    records: Do you really want to delete following records?
    no_data: No data to delete.
    delete_ok: Selected data were deleted.
cs:
  confirm_delete:
    title: Potvrzení smazání
    records: Opravdu si přejete smazat následující záznamy?
    no_data: Žádná data ke mazání.
    delete_ok: Vybraná data byla smazána.
</i18n>

<template>
  <v-card>
    <v-card-title class="headline">
      {{ $t("confirm_delete.title") }}
    </v-card-title>
    <v-card-text>
      <ImportBatchesList
        v-model="importBatches"
        v-if="importBatches && (loading || canDelete)"
        :import-batches="importBatches"
        :title-text="$t('confirm_delete.records')"
        :loading="loading"
      />
      <p v-else>{{ $t("confirm_delete.no_data") }}</p>
    </v-card-text>
    <v-card-actions>
      <v-btn
        color="error"
        class="ma-3"
        :loading="deleting"
        @click="deleteImportBatches()"
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
        {{ $t("actions.delete") }}
      </v-btn>
      <v-spacer />
      <v-btn color="secondary" @click="cancelDialog()" class="mr-2">
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
    slices: { required: true, type: Array },
  },
  data() {
    return {
      loading: false,
      deleting: false,
      importBatches: [],
    };
  },

  computed: {
    deleteUrl() {
      return "/api/import-batch/purge/";
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
        let response = await axios.post(this.lookupUrl, this.slices);
        this.importBatches = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading importBatches: " + error,
        });
      } finally {
        this.loading = false;
      }
    },
    async deleteImportBatches() {
      this.deleting = true;
      try {
        let response = await axios.post(this.deleteUrl, {
          batches: this.importBatchesKeys,
        });
        this.showSnackbar({
          content: this.$t("confirm_delete.delete_ok"),
          color: "success",
        });
        this.$emit("deleted");
      } catch (error) {
        this.showSnackbar({
          content: "Error deleting import batches: " + error,
        });
      } finally {
        this.deleting = false;
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
