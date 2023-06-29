<i18n lang="yaml">
en:
  add: Add annotation
  add_tt: Add a new annotation to make a note of important information

cs:
  add: Přidat poznámku
  add_tt: Přidejte novou poznámku pro uložení důležitých informacích
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
            <v-icon small class="mr-2">far fa-sticky-note</v-icon>
            {{ $t("add") }}
          </slot>
        </v-btn>
      </template>
      {{ $t("add_tt") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" max-width="1240px">
      <v-card>
        <v-card-title v-text="$t('add')"></v-card-title>
        <v-card-text>
          <AnnotationCreateModifyWidget
            ref="widget"
            :platform="platform"
            :fix-platform="fixPlatform"
            @saved="annotationSaved"
            @cancel="cancelEdit"
            @deleted="annotationSaved"
          />
        </v-card-text>
      </v-card>
    </v-dialog>
  </span>
</template>
<script>
import AnnotationCreateModifyWidget from "./AnnotationCreateModifyWidget";

export default {
  name: "AddAnnotationButton",
  components: { AnnotationCreateModifyWidget },
  props: {
    platform: {},
    text: { type: Boolean, default: false },
    small: { type: Boolean, default: false },
    fixPlatform: { type: Boolean, default: false },
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
      // this.$refs.widget.clean()
    },
    annotationSaved() {
      this.showDialog = false;
      this.$refs.widget.clean();
      this.$emit("update");
    },
  },
};
</script>
