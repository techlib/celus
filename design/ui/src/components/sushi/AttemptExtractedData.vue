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

export default {
  name: "AttemptExtractedData",
  props: {
    attempt: { required: true, type: Object },
  },

  computed: {
    headers() {
      return Object.entries(this.attempt.extracted_data).map(([key, value]) => {
        return [key, this.flatten(value)];
      });
    },
  },

  methods: {
    isEmpty,
    flatten(value) {
      if (isArray(value)) {
        return value.map((item) => (item.Value ? item.Value : item)).join(", ");
      }
      return value;
    },
  },
};
</script>
