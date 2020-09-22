<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  add: Upload new data from file

cs:
  add: Nahrát nová data ze souboru
</i18n>

<template>
  <span>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn
          @click="go()"
          :text="text"
          :small="small"
          :color="color"
          :disabled="disabled"
        >
          <v-icon class="mr-2" small>fa-upload</v-icon>
          {{ $t("actions.upload_data") }}
        </v-btn>
      </template>
      {{ $t("add") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" max-width="640px">
      <PlatformSelectionWidget>
        <template v-slot:actions>
          <v-btn @click="showDialog = false">{{ $t("actions.cancel") }}</v-btn>
        </template>
      </PlatformSelectionWidget>
    </v-dialog>
  </span>
</template>
<script>
import PlatformSelectionWidget from "./PlatformSelectionWidget";

export default {
  name: "ManualUploadButton",
  components: { PlatformSelectionWidget },
  props: {
    text: { type: Boolean, default: false },
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
    go() {
      this.showDialog = true;
    },
  },
};
</script>
