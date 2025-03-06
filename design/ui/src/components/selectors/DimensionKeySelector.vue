<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  possible_values: no possible value | {count} possible value | {count} possible values
  possible_values_truncated: There are too many possible values ({total}) to display all at once. Please use search to find relevant entries.

cs:
  possible_values: "{count} možná hodnota | {count} možné hodnoty | {count} možných hodnot"
  possible_values_truncated: Je k dispozici příliš mnoho hodnot ({total}), aby bylo možné je zobrazit najednou. Použijte vyhledávání k nalezení relevantních hodnot.
</i18n>

<template>
  <div class="full-width">
    <v-autocomplete
      v-if="!useTwoPanes"
      :items="items"
      v-model="selectedValues"
      @blur="blur()"
      :search-input="searchDebounced"
      multiple
      item-title="text"
      :item-value="dimension"
      :rules="rules"
      :hint="hint"
      persistent-hint
      chips
      closable-chips
      :disabled="disabled || readOnly"
      clearable
      clear-icon="fa fa-times"
      :loading="loading"
      hide-selected
    >
      <template v-slot:item="{ props, item }">
        <v-list-item v-bind="props" :title="item.raw.text"></v-list-item>
      </template>
    </v-autocomplete>
    <div v-else class="full-width">
      <TwoPaneSelector
        :items="items"
        v-model="selectedValues"
        :item-value="dimension"
        ref="twoPanes"
        :empty-hint="hint"
        :label="label"
        @update:modelValue="blur()"
      >
        <v-text-field
          v-model="searchDebounced"
          :loading="loading"
          :label="$t('labels.search')"
          class="mx-3 mt-3"
          variant="outlined"
          density="compact"
          clearable
        >
          <template #prepend-inner>
            <v-icon size="small" class="mt-1" icon="fa fa-search"></v-icon>
          </template>
        </v-text-field>
      </TwoPaneSelector>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import debounce from "lodash/debounce";
import TwoPaneSelector from "@/components/util/TwoPaneSelector";

export default {
  name: "DimensionKeySelector",
  components: { TwoPaneSelector },
  props: {
    queryUrl: { required: true, type: String },
    modelValue: { required: true, type: Array },
    dimension: { required: true, type: String },
    rules: { required: false, type: Array },
    translator: { required: false },
    name: { required: false, default: "" },
    disabled: { required: false, type: Boolean, default: false },
    disabledHint: { required: false, type: String, default: "" },
    readOnly: { required: false, type: Boolean, default: false }, // not exactly disabled, but almost :)
  },
  emits: ["update:modelValue"],

  data() {
    return {
      possibleValues: [],
      possibleValueCount: 0,
      try: null,
      // selectedValues: this.modelValue,
      loading: false,
      search: "",
      useTwoPanes: false,
      fetchPossibleValuesCancelTokenSource: null,
      idValidatorCancelTokenSource: null,
      truncated: false,
    };
  },

  computed: {
    possibleValuesUrl() {
      return this.queryUrl + `&dimension=${this.dimension}`;
    },
    items() {
      return Array.from(this.possibleValues);
    },
    label() {
      return `${this.name ?? this.dimension}`;
    },
    hint() {
      if (this.disabled || this.readOnly) {
        return "";
      }
      if (!this.truncated) {
        return this.$tc("possible_values", this.possibleValues.length);
      } else {
        return this.$t("possible_values_truncated", {
          showing: this.possibleValues.length,
          total: this.possibleValueCount,
        });
      }
    },
    selectedValues: {
      get() {
        return this.modelValue;
      },
      set(newValue) {
        this.$emit("update:modelValue", newValue);
      },
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (modelValue) {
        this.search = modelValue;
      }, 500),
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchPossibleValues() {
      let url = this.possibleValuesUrl;
      if (url && this.searchDebounced && this.searchDebounced.length > 0) {
        url += `&q=${this.searchDebounced}`;
      }
      if (url && !this.disabled) {
        if (this.fetchPossibleValuesCancelTokenSource) {
          this.fetchPossibleValuesCancelTokenSource.cancel(
            "new data requested",
          );
        }
        this.fetchPossibleValuesCancelTokenSource = axios.CancelToken.source();
        this.loading = true;
        try {
          let result = await axios.get(url, {
            cancelToken: this.fetchPossibleValuesCancelTokenSource.token,
          });
          this.fetchPossibleValuesCancelTokenSource = null;
          let truncated = result.data.cropped;
          let possibleValueCount = result.data.count;
          let possibleValues = [];
          if (!truncated) {
            possibleValues = result.data.values;
          }
          // if we have .values and it contains stuff that is not in possibleValues, we have to
          // refetch it - it can happen when loading truncated data
          let possiblePks = new Set(
            possibleValues.map((item) => item[this.dimension]),
          );
          let extraValues = this.modelValue.filter(
            (item) => !possiblePks.has(item),
          );
          if (extraValues.length) {
            let pks = extraValues.join(",");
            result = await axios.get(url + `&pks=${pks}`);
            result.data.values.forEach((item) => possibleValues.push(item));
          }
          // we fill the data in once it is all ready in order not to trigger intermittent updates
          this.possibleValues = possibleValues;
          this.possibleValueCount = possibleValueCount;
          this.truncated = truncated;
          // useTwoPanes must be only a one way switch - once we choose to use two panes, we must
          // keep it even if a filter reduces the number of options
          if (this.possibleValueCount > this.possibleValues.length) {
            this.useTwoPanes = true;
          }

          // deal with name translations
          await this.updateTranslator();

          // make sure that values no longer present are not amongst selected
          let pvs = new Set(
            this.possibleValues.map((item) => item[this.dimension]),
          );
          this.selectedValues = this.selectedValues.filter((item) =>
            pvs.has(item),
          );
        } catch (error) {
          if (axios.isCancel(error)) {
            console.debug("Request cancelled");
          } else {
            console.debug("Error", error);
            this.showSnackbar({
              content: `Could not fetch possible ${this.dimension} values: ${error}`,
              color: "error",
            });
          }
        } finally {
          this.loading = false;
        }
      }
    },
    blur() {
      this.$emit("update:modelValue", this.selectedValues);
      this.search = ""; // reset search so that it does not hang around
    },
    async updateTranslator() {
      if (this.translator) {
        await this.translator.prepareTranslation(
          this.possibleValues.map((item) => item[this.dimension]),
        );
        this.possibleValues.forEach((item) => {
          item.text =
            "" +
            (this.translator.translateKeyToString(
              item[this.dimension],
              this.$i18n.locale,
            ) ?? this.$t("blank_value"));
        });
        this.possibleValues.sort((a, b) => a.text.localeCompare(b.text));
      } else {
        this.possibleValues.forEach(
          (item) => (item["text"] = item[this.dimension]),
        );
        this.possibleValues.sort((a, b) => a.text > b.text);
      }
    },
    async itemIdValidator(ids) {
      if (this.idValidatorCancelTokenSource) {
        this.idValidatorCancelTokenSource.cancel();
      }
      try {
        let pks = ids.join(",");
        this.idValidatorCancelTokenSource = axios.CancelToken.source();
        let resp = await axios.get(this.possibleValuesUrl + `&pks=${pks}`, {
          cancelToken: this.idValidatorCancelTokenSource.token,
        });
        return resp.data.values.map((item) => item[this.dimension]);
      } catch (error) {
        if (axios.isCancel(error)) {
          console.debug("id validation cancelled");
        } else {
          console.debug("error when validating IDs", error);
        }
      } finally {
        this.idValidatorCancelTokenSource = null;
      }
    },
  },

  watch: {
    possibleValuesUrl() {
      this.fetchPossibleValues();
      if (this.useTwoPanes && this.$refs.twoPanes && !this.loading) {
        this.$refs.twoPanes.revalidateSelected(this.itemIdValidator);
      }
    },
    searchDebounced() {
      if (this.useTwoPanes) {
        this.fetchPossibleValues();
      }
    },
    selectedValues() {
      this.$emit("update:modelValue", this.selectedValues);
    },
    disabled() {
      if (!this.disabled) {
        this.fetchPossibleValues();
      }
    },
    readOnly() {
      if (!this.readOnly) {
        this.fetchPossibleValues();
      }
    },
    value() {
      this.selectedValues = this.value;
    },
  },

  async mounted() {
    if (this.readOnly) {
      if (this.translator) {
        await this.translator.prepareTranslation(this.selectedValues);
        this.possibleValues = this.selectedValues.map((id) => {
          let rec = {
            text: this.translator.translateKeyToString(id, this.$i18n.locale),
          };
          rec[this.dimension] = id;
          return rec;
        });
      }
    } else {
      await this.fetchPossibleValues();
    }
  },
};
</script>

<style scoped lang="scss">
.full-width {
  width: 100%;
}
</style>
