<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-btn color="primary" outlined :small="small" @click="showDialog = true">
    <v-icon small class="pr-2">fa fa-plus</v-icon>
    {{ $t("labels.new_tag") }}
    <v-dialog v-model="showDialog" max-width="720px">
      <EditTagWidget
        @saved="created"
        @close="showDialog = false"
        ref="widget"
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
