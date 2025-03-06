<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-select
          :items="dateRanges"
          :label="$t('labels.date_range')"
          v-model="selectedRangeName"
          item-value="name"
          item-title="nameLocal"
        >
          <template #item="{ props, item }">
            <v-list-item v-bind="props">
              <v-list-item-subtitle>
                <DateRangeText
                  :start="item.start"
                  :end="item.end"
                  class="float-right"
                ></DateRangeText>
                <div
                  class="d-flex"
                  :class="{
                    'justify-content-between': item.raw.desc,
                    'justify-content-end': !item.raw.desc,
                  }"
                >
                  <span v-if="item.raw.desc" class="text-caption">
                    {{ $t(item.raw.desc) }}
                  </span>
                  <span>{{
                    item.raw.start
                      ? `${formatDate(item.raw.start)} - ${formatDate(
                          item.raw.end,
                        )}`
                      : ""
                  }}</span>
                </div>
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row v-if="dateRange.custom">
      <!-- start date selector -->
      <v-col cols="12" :sm="6">
        <DatePicker v-model="start" :max-date="endRaw">
          <template v-slot:activator="{ props }">
            <v-text-field
              v-model="DateForTextStart"
              label="Start"
              readonly
              v-bind="props"
            >
              <template v-slot:prepend>
                <v-icon color="primary">fas fa-calendar-alt</v-icon>
              </template>
            </v-text-field>
          </template>
        </DatePicker>
      </v-col>
      <!-- end date selector -->
      <v-col cols="12" :sm="6">
        <DatePicker v-model="end" :min-date="startRaw">
          <template v-slot:activator="{ props }">
            <v-text-field
              v-model="DateForTextEnd"
              label="End"
              readonly
              v-bind="props"
            >
              <template v-slot:prepend>
                <v-icon color="primary">fas fa-calendar-alt</v-icon>
              </template>
            </v-text-field>
          </template>
        </DatePicker>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import { ymDateParse } from "@/libs/dates";
import DateRangeText from "@/components/util/DateRangeText";
import MonthEntry from "./util/MonthEntry.vue";
import DatePicker from "@/components/DatePicker.vue";

export default {
  name: "DateRangeSelector",
  components: { DateRangeText, MonthEntry, DatePicker },
  data() {
    return {
      menuStart: false,
      menuEnd: false,
    };
  },
  computed: {
    ...mapState({
      dateRangeName: "dateRangeName",
      startRaw: "dateRangeStart",
      endRaw: "dateRangeEnd",
    }),
    ...mapGetters({
      dateRange: "selectedDateRange",
      dateRangesRaw: "dateRanges",
    }),
    dateRanges() {
      return this.dateRangesRaw.map((item, index) => {
        return { ...item, nameLocal: this.$i18n.t(item.name), index: index };
      });
    },
    selectedRangeName: {
      get() {
        return this.dateRangeName;
      },
      set(value) {
        this.setDateRangeName(value);
      },
    },
    start: {
      get() {
        return {
          month: this.startRaw.getMonth(),
          year: this.startRaw.getFullYear(),
        };
      },
      set(value) {
        if (value && typeof value === "object" && "month" in value) {
          const day = value.day || 1;
          this.setDateRangeStart(new Date(value.year, value.month, day));
        } else if (typeof value === "string") {
          let date = ymDateParse(value);
          this.setDateRangeStart(date);
        } else {
          this.setDateRangeStart(value);
        }
      },
    },
    end: {
      get() {
        return {
          month: this.endRaw.getMonth(),
          year: this.endRaw.getFullYear(),
        };
      },
      set(value) {
        if ("month" in value) {
          this.setDateRangeEnd(new Date(value.year, value.month));
        } else {
          this.setDateRangeEnd(value);
        }
      },
    },
    DateForTextStart() {
      const month = this.start.month + 1;
      const year = this.start.year;
      if (month < 10) {
        return `${year} - 0${month}`;
      }
      return `${year} - ${month}`;
    },
    DateForTextEnd() {
      const month = this.end.month + 1;
      const year = this.end.year;
      if (month < 10) {
        return `${year} - 0${month}`;
      }
      return `${year} - ${month}`;
    },
  },
  methods: {
    ...mapActions({
      setDateRangeName: "changeDateRangeObject",
      setDateRangeStart: "changeDateRangeStart",
      setDateRangeEnd: "changeDateRangeEnd",
    }),
    allowedEndMonths(value) {
      let start = this.start;
      if (start) {
        return value >= start;
      }
      return true;
    },
    formatDate(dateString) {
      if (dateString) {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        return `${year}-${month}`;
      } else {
        return this.$t("today");
      }
    },
    allowedStartMonths(value) {
      let end = this.end;
      if (end) {
        return value <= end;
      }
      return true;
    },
  },
};
</script>

<style scoped>
.justify-content-between {
  justify-content: space-between;
}
.justify-content-end {
  justify-content: flex-end;
}

:deep(.v-input__details) {
  display: none;
}
</style>
