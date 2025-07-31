<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-btn
    :color="color"
    :size="small ? 'small' : undefined"
    @click.stop="showDialog = true"
    :icon="icon"
    :density="comfortable ? 'comfortable' : 'default'"
    :variant="variantOfButton"
    :elevation="
      variantOfButton === 'outlined' || variantOfButton === 'text' ? 0 : 2
    "
    v-bind="$attrs"
  >
    <v-icon size="small">fa fa-plus</v-icon>
    <span v-if="!icon" class="ml-2">{{ $t("labels.new_tag") }}</span>
    <v-dialog
      v-if="showDialog"
      v-model="showDialog"
      max-width="720"
      :persistent="true"
    >
      <EditTagWidget
        @saved="created"
        @close="showDialog = false"
        ref="widget"
        :fixed-tag-class="tagClass"
        :scope="scope"
      ></EditTagWidget>
    </v-dialog>
  </v-btn>
</template>

<script>
import EditTagWidget from "@/components/tags/EditTagWidget";

export default {
  name: "AddTagButton",

  components: { EditTagWidget },

  props: {
    outlined: { type: Boolean, default: false },
    text: { type: Boolean, default: false },
    comfortable: { type: Boolean },
    flat: { type: Boolean, default: false },
    small: { type: Boolean, default: false },
    color: { type: String, default: "" },
    tagClass: { type: Object, default: null },
    icon: { type: Boolean, default: false },
    scope: {
      type: String,
      validator(value) {
        return ["title", "platform", "organization"].includes(value);
      },
      required: false,
    },
  },

  data() {
    return {
      showDialog: false,
    };
  },

  computed: {
    variantOfButton() {
      if (this.text) return "text";
      if (this.outlined) return "outlined";
      if (this.flat) return "flat";
      return "undefined";
    },
  },

  methods: {
    created(data) {
      this.$emit("saved", data);
      this.showDialog = false;
    },
  },

  watch: {
    showDialog() {
      if (this.showDialog && this.$refs.widget) {
        // clear up the name to prevent the user from trying to create the same
        // tag over and over
        this.$refs.widget.clearName();
        this.$refs.widget.reload();
      }
    },
  },
};
</script>

<style scoped>
.button-border-color {
}
</style>
