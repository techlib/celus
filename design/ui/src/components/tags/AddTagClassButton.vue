<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-btn color="primary" outlined :small="small" @click="showDialog = true">
    <v-icon small class="pr-2">fa fa-plus</v-icon>
    {{ $t("labels.new_tag_class") }}
    <v-dialog v-model="showDialog" max-width="720px">
      <EditTagClassWidget
        @saved="created"
        @close="showDialog = false"
        ref="widget"
      />
    </v-dialog>
  </v-btn>
</template>

<script>
import EditTagClassWidget from "@/components/tags/EditTagClassWidget";

export default {
  name: "AddTagClassButton",

  components: { EditTagClassWidget },

  props: {
    small: { type: Boolean, default: false },
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
      }
    },
  },
};
</script>

<style scoped></style>
