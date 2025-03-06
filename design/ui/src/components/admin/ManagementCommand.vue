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
                v-bind="extraAttrs(arg)"
                :variant="arg.type !== 'bool' ? 'underlined' : 'default'"
                :density="arg.type === 'bool' ? 'compact' : 'default'"
                :class="arg.type === 'bool' ? 'mt-4' : ''"
              >
              </component>
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
                  width="200px"
                  :hide-details="true"
                >
                  <template #label>
                    {{ $t("really_do_it") }}
                    <v-icon
                      color="warning"
                      size="small"
                      class="ps-1 icon_warning"
                      >fa fa-exclamation-triangle</v-icon
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
        <v-alert type="error" variant="outlined" class="overflow-auto">
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
        <pre>
          <div v-for="(line, index) in textToLines(result.log)" :key="index" :class="typeToColor(line.type) + '--text'">{{ line.text }}</div>
        </pre>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { defineComponent } from "vue";
import cancellation from "@/mixins/cancellation";
// import { VCheckbox, VTextField, VFileInput } from "vuetify/lib";
import capitalize from "lodash/capitalize";
import OrganizationSelectionWidget from "@/components/selectors/OrganizationSelectionWidget.vue";

export default defineComponent({
  name: "ManagementCommand",

  mixins: [cancellation],

  components: {
    // VCheckbox,
    // VTextField,
    // VFileInput,
    OrganizationSelectionWidget,
  },

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
        if (typeof value === "object" && value !== null) {
          formData.append(key, value[0]);
        }
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
      // first check if the metavar is a special value that indicates a
      // list of choices from a model (e.g. _ORG_ID_ means list of organizations)
      if (
        arg.metavar &&
        arg.metavar.startsWith("_") &&
        arg.metavar.endsWith("_")
      ) {
        if (arg.metavar.startsWith("_ORG_ID")) {
          return "OrganizationSelectionWidget";
        }
      }
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
    extraAttrs(arg) {
      if (arg.type === "int") {
        return {
          type: "number",
        };
      }
    },
    textToLines(text) {
      let out = [];
      text.split("\n").forEach((line) => {
        let parts = line.split("::");
        if (parts.length === 2) {
          out.push({ type: parts[0].toLowerCase(), text: parts[1] });
        } else {
          out.push({ type: "text", text: line });
        }
      });
      return out;
    },
    typeToColor(type) {
      if (!["error", "warning", "info", "success"].includes(type)) {
        return "grey";
      }
      return type;
    },
  },

  watch: {
    command: {
      immediate: true,
      handler() {
        this.result = null;
        this.formData = {};
        for (let arg of this.command.args) {
          this.formData[arg.name] = arg.default;
        }
      },
    },
  },
});
</script>

<style lang="scss">
.v-input__details {
  min-height: 0;
}
.icon_warning {
  width: 30px;
}
.v-label {
  word-break: normal !important;
}
</style>
