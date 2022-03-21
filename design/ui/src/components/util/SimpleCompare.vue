<template>
  <div class="text-right pr-1">
    <span v-if="value == null">-</span>
    <div v-else>
      <span>{{ formatInteger(value) }}</span>
      <v-tooltip bottom v-if="otherValueTooltip && otherValue && diff">
        <template v-slot:activator="{ on }">
          <span v-on="on" class="font-weight-light">
            (<v-icon x-small :color="diffColor">{{ diffIcon }}</v-icon>
            {{ formatInteger(diff) }})
          </span>
        </template>
        <span>{{ otherValueTooltip }}</span>
      </v-tooltip>
      <span v-else-if="diff">
        (<v-icon x-small :color="diffColor">{{ diffIcon }}</v-icon>
        {{ formatInteger(diff) }})
      </span>
    </div>
  </div>
</template>

<script>
import { formatInteger } from "@/libs/numbers";

export default {
  name: "SimpleCompare",

  props: {
    value: { required: false, type: Number },
    negate: { default: false, type: Boolean },
    otherValue: { required: false, type: Number },
    otherValueTooltip: { default: null, type: String },
  },

  computed: {
    diffIcon() {
      if (this.value != null && this.otherValue != null) {
        if (this.value > this.otherValue) {
          if (this.negate) {
            return "fas fa-long-arrow-alt-down";
          } else {
            return "fas fa-long-arrow-alt-up";
          }
        } else if (this.value < this.otherValue) {
          if (this.negate) {
            return "fas fa-long-arrow-alt-up";
          } else {
            return "fas fa-long-arrow-alt-down";
          }
        }
      }
      return null;
    },
    diffColor() {
      if (this.value != null && this.otherValue != null) {
        if (this.value > this.otherValue) {
          if (this.negate) {
            return "error";
          } else {
            return "success";
          }
        } else if (this.value < this.otherValue) {
          if (this.negate) {
            return "success";
          } else {
            return "error";
          }
        }
      }
      return "secondary";
    },
    diff() {
      if (this.value != null && this.otherValue != null) {
        return Math.abs(this.value - this.otherValue);
      }
      return null;
    },
  },

  methods: {
    formatInteger,
  },
};
</script>

<style scoped></style>
