<i18n lang="yaml">
en:
  add: Add annotation

cs:
  add: Přidat poznámku
</i18n>

<template>
  <span>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn @click="showDialog = true" v-on="on" :text="text" :small="small">
          <slot>
            <v-icon small class="mr-2">far fa-sticky-note</v-icon>
            {{ $t("add") }}
          </slot>
        </v-btn>
      </template>
      {{ $t("add") }}
    </v-tooltip>
    <v-dialog v-model="showDialog" max-width="1240px">
      <v-card>
        <v-card-title v-text="$t('add')"></v-card-title>
        <v-card-text>
          <AnnotationCreateModifyWidget
            ref="widget"
            :platform="platform"
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
