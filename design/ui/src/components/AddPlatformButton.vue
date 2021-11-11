<i18n lang="yaml">
en:
  add: Add platform

cs:
  add: Přidat platformu
</i18n>

<template>
  <span>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn
          @click="showDialog = true"
          v-on="on"
          :text="text"
          :small="small"
          :color="color"
        >
          <slot>
            <v-icon small class="mr-2">fas fa-plus</v-icon>
            {{ $t("add") }}
          </slot>
        </v-btn>
      </template>
      {{ $t("add") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" :max-width="dialogMaxWidth">
      <PlatformEditDialog
        v-if="showDialog"
        @close="cancelEdit()"
        @saved="platformSaved"
        key="add"
      />
    </v-dialog>
  </span>
</template>
<script>
import PlatformEditDialog from "./PlatformEditDialog";

export default {
  name: "AddPlatformButton",
  components: { PlatformEditDialog },
  props: {
    dialogMaxWidth: { type: String, default: "1240px" },
    text: { type: Boolean, default: false },
    small: { type: Boolean, default: false },
    color: { type: String, default: "" },
  },
  data() {
    return {
      showDialog: false,
    };
  },
  methods: {
    cancelEdit() {
      this.showDialog = false;
    },
    platformSaved(platform) {
      console.log(platform);
      this.showDialog = false;
      this.$emit("update-platforms", platform);
    },
  },
};
</script>
