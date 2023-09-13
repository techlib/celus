<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-btn
    :color="color"
    :small="small"
    @click="showDialog = true"
    :icon="icon"
    v-on="$listeners"
    v-bind="$attrs"
  >
    <v-icon small>fa fa-plus</v-icon>
    <span v-if="!icon" class="pl-2">{{ $t("labels.new_tag") }}</span>
    <v-dialog v-model="showDialog" max-width="720px">
      <EditTagWidget
        @saved="created"
        @close="showDialog = false"
        ref="widget"
        :fixed-tag-class="tagClass"
        :scope="scope"
      />
    </v-dialog>
  </v-btn>
</template>

<script>
import EditTagWidget from "@/components/tags/EditTagWidget";

export default {
  name: "AddTagButton",

  components: { EditTagWidget },

  props: {
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

<style scoped></style>
