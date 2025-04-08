<i18n lang="yaml">
en:
  add: Add platform
  add_tt: If you do not find a platform in our extensive list, you can add one here

cs:
  add: Přidat platformu
  add_tt: Pokud nenajdete platformu v našem rozsáhlém seznamu, můžete ji přidat zde
</i18n>

<template>
  <span>
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props }">
        <v-btn
          @click.stop="showDialog = true"
          v-bind="props"
          :variant="text ? 'text' : 'flat'"
          :size="small ? 'small' : 'default'"
          :color="color"
          :elevation="text ? 0 : 2"
        >
          <slot>
            <v-icon size="small" class="mr-2">fas fa-plus</v-icon>
            {{ $t("add") }}
          </slot>
        </v-btn>
      </template>
      {{ $t("add_tt") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" :max-width="dialogMaxWidth">
      <PlatformEditDialog
        v-if="showDialog"
        @close="cancelEdit"
        @saved="platformSaved"
        key="add"
      ></PlatformEditDialog>
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
    text: { type: Boolean },
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
      this.showDialog = false;
      this.$emit("update-platforms", platform);
    },
  },
};
</script>
