<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <v-dialog v-model="show" max-width="640px">
    <v-card class="pa-3">
      <v-card-title>{{ $t("error") }}</v-card-title>
      <v-card-text>
        <v-list>
          <v-list-item
            v-for="(error, index) in errors"
            :key="index"
            class="px-0"
          >
            <v-list-item-avatar>
              <v-icon color="error">fa-exclamation-circle</v-icon>
            </v-list-item-avatar>
            <v-list-item-content>{{ error }}</v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="close()">{{ $t("dismiss") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script>
export default {
  name: "ErrorDialog",

  props: {
    errors: { type: Array, required: true },
    value: { type: Boolean, required: false, default: true },
  },

  data() {
    return {
      show: this.value,
    };
  },

  methods: {
    close() {
      this.show = false;
      this.$emit("update", false);
    },
  },

  watch: {
    value(value) {
      this.show = value;
    },
  },
};
</script>
