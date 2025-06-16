<i18n lang="yaml">
en:
  month_start: Start month
  month_end: End month

cs:
  month_start: Počáteční měsíc
  month_end: Koncový měsíc
</i18n>

<template>
  <div
    class="d-flex"
    :style="sm ? 'flex-direction: column' : 'flex-direction: row'"
  >
    <span class="pr-3" :style="computedStyle">
      <MonthEntry
        v-model="startMonth"
        :label="textStart"
        :max-month="endMonth"
        :disabled="disabled"
        :clearable="clearable"
        validate-pair
      ></MonthEntry>
    </span>
    <span class="pr-3" :style="computedStyle">
      <MonthEntry
        v-model="endMonth"
        :label="textEnd"
        :disabled="disabled"
        :clearable="clearable"
      ></MonthEntry>
    </span>
  </div>
</template>

<script>
import MonthEntry from "@/components/util/MonthEntry";
export default {
  name: "FromToMonthEntry",

  components: { MonthEntry },

  emits: ["update:modelValue"],

  props: {
    w: { type: Boolean, default: false },
    sm: { type: Boolean },
    modelValue: { required: true, type: Object },
    startLabel: { required: false, type: String, default: null },
    endLabel: { required: false, type: String, default: null },
    disabled: { required: false, type: Boolean, default: false },
    clearable: { required: false, type: Boolean, default: true },
  },

  data() {
    return {
      startMonth: null,
      endMonth: null,
    };
  },

  computed: {
    textStart() {
      return this.startLabel ?? this.$t("month_start");
    },
    textEnd() {
      return this.endLabel ?? this.$t("month_end");
    },
    computedStyle() {
      return {
        "min-width": "150px",
        width: this.w ? "50%" : "100%",
      };
    },
  },

  watch: {
    startMonth() {
      this.$emit("update:modelValue", {
        start: this.startMonth,
        end: this.endMonth,
      });
    },
    endMonth() {
      this.$emit("update:modelValue", {
        start: this.startMonth,
        end: this.endMonth,
      });
    },
    modelValue: {
      immediate: true,
      handler() {
        this.startMonth = this.modelValue.start;
        this.endMonth = this.modelValue.end;
      },
    },
  },
};
</script>

<style scoped></style>
