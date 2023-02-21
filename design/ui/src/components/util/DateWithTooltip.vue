<template>
  <v-tooltip bottom>
    <template #activator="{ on }">
      <span class="date" v-on="on">{{ date }}</span>
    </template>
    <span>{{ localDate }}</span>
  </v-tooltip>
</template>

<script>
import format from "date-fns/format";

export default {
  name: "DateWithTooltip",

  props: {
    date: {
      type: String,
      required: true,
    },
  },

  computed: {
    localDate() {
      if (!this.date) {
        return "";
      }
      const dateObj = new Date(this.date);
      return format(dateObj, "PP");
    },
  },
};
</script>

<style lang="scss" scoped>
.date {
  font-size: 75%;
  color: #888888;
  margin-left: 0.4rem;
  line-height: normal;
}
</style>
