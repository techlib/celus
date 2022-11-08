<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    max-width="290"
    nudge-bottom="48"
  >
    <template v-slot:activator="{ on, attrs }">
      <v-text-field
        :value="color"
        clearable
        :label="label"
        readonly
        v-bind="attrs"
        v-on="on"
        @click:clear="color = defaultColor"
      >
        <template #prepend-inner>
          <v-icon :color="color">fa-square</v-icon>
        </template>
      </v-text-field>
    </template>
    <v-card class="pa-0 ma-0">
      <v-card-text class="pa-0 ma-0">
        <v-color-picker
          v-if="!hideSwatches"
          v-model="color"
          @change="menu = false"
          show-swatches
          :swatches="swatches"
          hide-canvas
          hide-inputs
          hide-sliders
          class="pb-0 mb-0"
        />
        <div>
          <v-expansion-panels v-model="showCustom" flat>
            <v-expansion-panel>
              <v-expansion-panel-header>
                {{ $t("labels.custom") }}
              </v-expansion-panel-header>
              <v-expansion-panel-content>
                <v-color-picker v-model="color" @change="menu = false" />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>
      </v-card-text>
    </v-card>
  </v-menu>
</template>
<script>
export default {
  name: "ColorEntry",
  props: {
    value: { type: String, default: "#e2e2e2" },
    label: { type: String, default: "Color" },
    hideSwatches: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      menu: false,
      defaultColor: "#9E9E9E",
      swatches: [
        ["#F44336", "#E91E63", "#9C27B0", "#673AB7"],
        ["#3F51B5", "#2196F3", "#03A9F4", "#00BCD4"],
        ["#009688", "#4CAF50", "#8BC34A", "#CDDC39"],
        ["#FFEB3B", "#FFC107", "#FF9800", "#FF5722"],
        ["#795548", "#757575", "#000000", "#FFFFFF"],
      ],
      showCustom: false,
    };
  },

  computed: {
    color: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      },
    },
  },
};
</script>

<style lang="scss" scoped>
.color-preview {
  width: 2rem;
}
</style>
