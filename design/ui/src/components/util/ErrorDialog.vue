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
            <v-list-item :avatar="true">
              <v-icon color="error" class="my-1"
                >fa fa-exclamation-circle</v-icon
              >
            </v-list-item>
            <v-list-item class="error_text">{{ error }}</v-list-item>
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="elevated" @click="close()">{{ $t("dismiss") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "ErrorDialog",

  props: {
    errors: { type: Array, required: true },
    modelValue: { type: Boolean, required: false, default: true },
  },

  data() {
    return {
      show: this.modelValue,
    };
  },

  methods: {
    close() {
      this.show = false;
      this.$emit("update:modelValue", false);
    },
  },

  watch: {
    value(value) {
      this.show = value;
    },
  },
};
</script>

<style scoped>
:deep(.v-list-item__content) {
  display: flex;
  align-items: center;
}
.error_text {
  font-size: 14px;
  max-width: 500px;
}

@media (max-width: 700px) {
  .error_text {
    max-width: 70vw;
  }
}

@media (max-width: 470px) {
  .error_text {
    max-width: 60vw;
  }
}
</style>
