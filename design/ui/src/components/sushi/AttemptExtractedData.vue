<i18n lang="yaml">
en:
  headers: Headers

cs:
  headers: Hlavičky
</i18n>

<template>
  <div v-if="attempt && !isEmpty(attempt.extracted_data)">
    <span class="font-weight-bold pr-4"
      >{{ $t("headers") }}<span class="font-weight-regular">:</span></span
    >
    <span v-for="[header, value] in headers" :key="header">
      <span class="caption pr-1">{{ header }}:</span>
      <span class="pr-4">{{ value }}</span>
    </span>
  </div>
</template>

<script>
import isArray from "lodash/isArray";
import isEmpty from "lodash/isEmpty";
import { counterHeaderRepr } from "@/libs/counter_header.js";
import { counterVersionToStr } from "@/libs/sushi.js";

export default {
  name: "AttemptExtractedData",
  props: {
    attempt: { required: true, type: Object },
    counterReportVersion: { required: true, type: Number },
  },

  computed: {
    headers() {
      return Object.entries(
        counterHeaderRepr(
          this.attempt.extracted_data,
          counterVersionToStr(this.counterReportVersion),
        ),
      );
    },
  },

  methods: {
    isEmpty,
  },
};
</script>
