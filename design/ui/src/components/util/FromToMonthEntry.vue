<i18n lang="yaml">
en:
  month_start: Start month
  month_end: End month

cs:
  month_start: Počáteční měsíc
  month_end: Koncový měsíc
</i18n>

<template>
  <div class="d-flex">
    <span class="pr-4">
      <MonthEntry
        v-model="startMonth"
        :label="textStart"
        :allowed-months="allowedStartMonths"
        :disabled="disabled"
      ></MonthEntry>
    </span>
    <MonthEntry
      v-model="endMonth"
      :label="textEnd"
      :allowed-months="allowedEndMonths"
      :disabled="disabled"
    ></MonthEntry>
  </div>
</template>

<script>
import MonthEntry from "@/components/util/MonthEntry";
export default {
  name: "FromToMonthEntry",

  components: { MonthEntry },

  props: {
    value: { required: true, type: Object },
    startLabel: { required: false, type: String, default: null },
    endLabel: { required: false, type: String, default: null },
    disabled: { required: false, type: Boolean, default: false },
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
  },

  methods: {
    allowedEndMonths(value) {
      if (this.startMonth) {
        return value >= this.startMonth;
      }
      return true;
    },
    allowedStartMonths(value) {
      if (this.endMonth) {
        return value <= this.endMonth;
      }
      return true;
    },
  },

  watch: {
    startMonth() {
      this.$emit("input", { start: this.startMonth, end: this.endMonth });
    },
    endMonth() {
      this.$emit("input", { start: this.startMonth, end: this.endMonth });
    },
    value: {
      immediate: true,
      handler() {
        this.startMonth = this.value.start;
        this.endMonth = this.value.end;
      },
    },
  },
};
</script>

<style scoped></style>
