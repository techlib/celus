<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  add: Upload new data from file

cs:
  add: Nahrát nová data ze souboru
</i18n>

<template>
  <div>
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props }">
        <v-btn
          @click="openDialog"
          :text="text"
          :size="small ? 'small' : 'default'"
          :color="color"
          :disabled="disabled"
          v-bind="props"
        >
          <v-icon class="mr-2" size="small" icon="fa fa-upload"></v-icon>
          {{ $t("actions.upload_data") }}
        </v-btn>
      </template>
      {{ $t("add") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" max-width="640px">
      <PlatformSelectionWidget allow-create>
        <template v-slot:actions>
          <v-btn @click="showDialog = false" variant="flat" elevation="2">{{
            $t("actions.cancel")
          }}</v-btn>
        </template>
      </PlatformSelectionWidget>
    </v-dialog>
  </div>
</template>

<script>
import PlatformSelectionWidget from "./selectors/PlatformSelectionWidget";

export default {
  name: "ManualUploadButton",
  components: { PlatformSelectionWidget },
  props: {
    text: { type: String },
    small: { type: Boolean, default: false },
    color: { type: String },
    disabled: { type: Boolean, default: false },
  },
  data() {
    return {
      showDialog: false,
    };
  },
  methods: {
    openDialog() {
      this.showDialog = true;
    },
  },
};
</script>
