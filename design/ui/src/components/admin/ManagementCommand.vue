<i18n lang="yaml">
en:
  run_command: Run command
  really_run_command: Really run command
  test_run_command: Test run command
  really_do_it: Really do it!

cs:
  run_command: Spustit příkaz
  really_run_command: Opravdu spustit příkaz
  test_run_command: Spustit test příkazu
  really_do_it: Opravdu to udělat!
</i18n>

<template>
  <v-container fluid class="pa-0">
    <v-row>
      <v-col>
        <v-card elevation="6">
          <v-card-title>{{ command.name }}</v-card-title>
          <v-card-subtitle class="font-weight-light">{{
            command.help
          }}</v-card-subtitle>
          <v-card-text>
            <v-form>
              <component
                v-for="arg in command.args"
                :is="chooseComponent(arg)"
                :key="arg.name"
                :label="prettifyName(arg.name)"
                :hint="arg.help"
                persistent-hint
                v-model="formData[arg.name]"
              />
              <div class="pt-8 d-flex align-center">
                <div style="width: 240px">
                  <v-btn
                    @click="sendData"
                    :color="submitColor"
                    :disabled="uploading"
                    :loading="uploading"
                    >{{ submitText }}
                  </v-btn>
                </div>
                <v-checkbox
                  v-if="usesDoIt"
                  v-model="formData.doit"
                  color="warning"
                  class="ps-8"
                >
                  <template #label>
                    {{ $t("really_do_it") }}
                    <v-icon color="warning" small class="ps-1"
                      >fa-exclamation-triangle</v-icon
                    >
                  </template>
                </v-checkbox>
              </div>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="result && result.exception">
      <v-col cols="1" class="text-caption">exception:</v-col>
      <v-col>
        <v-alert type="error" outlined class="overflow-auto">
          <pre class="pt-1">
            {{ result.exception }}
          </pre>
        </v-alert>
      </v-col>
    </v-row>
    <v-row v-if="result">
      <v-col cols="1" class="text-caption">stderr:</v-col>
      <v-col>
        <pre>{{ result.stderr }}</pre>
      </v-col>
    </v-row>
    <v-row v-if="result">
      <v-col cols="1" class="text-caption">stdout:</v-col>
      <v-col>
        <pre>{{ result.stdout }}</pre>
      </v-col>
    </v-row>
    <v-row v-if="result">
      <v-col cols="1" class="text-caption">log:</v-col>
      <v-col>
        <pre>{{ result.log }}</pre>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { defineComponent } from "vue";
import cancellation from "@/mixins/cancellation";
import { VCheckbox, VTextField, VFileInput } from "vuetify/lib";
import capitalize from "lodash/capitalize";

export default defineComponent({
  name: "ManagementCommandList",

  mixins: [cancellation],

  components: { VCheckbox, VTextField, VFileInput },

  props: {
    command: {
      type: Object,
      required: true,
    },
  },

  data() {
    return {
      result: null,
      formData: {},
      uploading: false,
    };
  },

  computed: {
    usesDoIt() {
      return this.command && this.command.uses_doit;
    },
    submitText() {
      return this.usesDoIt
        ? this.formData.doit
          ? this.$t("really_run_command")
          : this.$t("test_run_command")
        : this.$t("run_command");
    },
    submitColor() {
      return !this.usesDoIt || this.formData.doit ? "warning" : "success";
    },
  },

  methods: {
    async sendData() {
      this.result = null;
      let formData = new FormData();
      for (let [key, value] of Object.entries(this.formData)) {
        if (value !== null) formData.append(key, value);
      }
      this.uploading = true;
      let result = await this.http({
        url: `/api/management/command/${this.command.name}/run/`,
        method: "POST",
        data: formData,
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (!result.error) {
        this.result = result.response.data;
      }
      this.uploading = false;
    },
    chooseComponent(arg) {
      switch (arg.type) {
        case "bool":
          return "v-checkbox";
        case "file":
          return "v-file-input";
        default:
          return "v-text-field";
      }
    },
    prettifyName(name) {
      return capitalize(name.replace(/_/g, " "));
    },
  },

  watch: {
    command: {
      immediate: true,
      handler() {
        this.result = null;
        this.formData = {};
      },
    },
  },
});
</script>

<style scoped lang="scss"></style>
