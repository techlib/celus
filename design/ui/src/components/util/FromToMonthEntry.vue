<i18n lang="yaml">
en:
  date_start: Start date
  date_end: End date

cs:
  date_start: Počáteční datum
  date_end: Koncové datum
</i18n>

<template>
  <div class="d-flex">
    <span class="pr-4">
      <MonthEntry
        v-model="startDate"
        :label="textStart"
        :allowed-months="allowedStartMonths"
        :disabled="disabled"
      ></MonthEntry>
    </span>
    <MonthEntry
      v-model="endDate"
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
      startDate: null,
      endDate: null,
    };
  },

  computed: {
    textStart() {
      return this.startLabel ?? this.$t("date_start");
    },
    textEnd() {
      return this.endLabel ?? this.$t("date_end");
    },
  },

  methods: {
    allowedEndMonths(value) {
      if (this.startDate) {
        return value >= this.startDate;
      }
      return true;
    },
    allowedStartMonths(value) {
      if (this.endDate) {
        return value <= this.endDate;
      }
      return true;
    },
  },

  watch: {
    startDate() {
      this.$emit("input", { start: this.startDate, end: this.endDate });
    },
    endDate() {
      this.$emit("input", { start: this.startDate, end: this.endDate });
    },
    value: {
      immediate: true,
      handler() {
        this.startDate = this.value.start;
        this.endDate = this.value.end;
      },
    },
  },
};
</script>

<style scoped></style>
