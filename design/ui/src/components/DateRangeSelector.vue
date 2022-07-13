<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-select
          :items="dateRanges"
          :label="$t('labels.date_range')"
          v-model="selectedRangeIndex"
          item-value="index"
          item-text="nameLocal"
        >
          <template #item="{ item }">
            <v-list-item-content>
              <v-list-item-title v-text="$t(item.name)"></v-list-item-title>
              <v-list-item-subtitle>
                <DateRangeText
                  :start="item.start"
                  :end="item.end"
                  class="float-right"
                />
                <span v-if="item.desc" class="text-caption">
                  {{ $t(item.desc) }}
                </span>
              </v-list-item-subtitle>
            </v-list-item-content>
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row v-if="dateRange.custom">
      <!-- start date selector -->
      <v-col cols="12" :sm="6">
        <v-menu
          v-model="menuStart"
          transition="scale-transition"
          offset-y
          min-width="290px"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="start"
              label="Start"
              prepend-icon="fa-calendar-alt"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="start"
            type="month"
            no-title
            :locale="$i18n.locale"
            :allowed-dates="allowedStartMonths"
          ></v-date-picker>
        </v-menu>
      </v-col>
      <!-- end date selector -->
      <v-col cols="12" :sm="6">
        <v-menu
          v-model="menuEnd"
          transition="scale-transition"
          offset-y
          min-width="290px"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              v-model="end"
              label="End"
              prepend-icon="fa-calendar-alt"
              readonly
              v-on="on"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="end"
            type="month"
            no-title
            scrollable
            :locale="$i18n.locale"
            :allowed-dates="allowedEndMonths"
          >
          </v-date-picker>
        </v-menu>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import { ymDateFormat, parseDateTime } from "@/libs/dates";
import DateRangeText from "@/components/util/DateRangeText";

export default {
  name: "DateRangeSelector",
  components: { DateRangeText },
  data() {
    return {
      menuStart: false,
      menuEnd: false,
    };
  },
  computed: {
    ...mapState({
      dateRangesRaw: "dateRanges",
      dateRangeIndex: "dateRangeIndex",
      startRaw: "dateRangeStart",
      endRaw: "dateRangeEnd",
    }),
    ...mapGetters({
      dateRange: "selectedDateRange",
    }),
    dateRanges() {
      return this.dateRangesRaw.map((item, index) => {
        return { ...item, index: index, nameLocal: this.$i18n.t(item.name) };
      });
    },
    selectedRangeIndex: {
      get() {
        return this.dateRangeIndex;
      },
      set(value) {
        this.setDateRangeIndex(value);
      },
    },
    start: {
      get() {
        return ymDateFormat(this.startRaw);
      },
      set(value) {
        this.setDateRangeStart(parseDateTime(value));
      },
    },
    end: {
      get() {
        return ymDateFormat(this.endRaw);
      },
      set(value) {
        this.setDateRangeEnd(parseDateTime(value));
      },
    },
  },
  methods: {
    ...mapActions({
      setDateRangeIndex: "changeDateRangeObject",
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

<style scoped></style>
