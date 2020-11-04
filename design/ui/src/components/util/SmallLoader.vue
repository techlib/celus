<template>
  <span>
    <v-icon v-if="value === null" class="mr-2">far fa-hourglass</v-icon>
    <v-icon v-else-if="value" class="mr-2">fa fa-spinner fa-spin</v-icon>
    <v-icon v-else class="mr-2">far fa-check-circle</v-icon>
    <slot></slot>
  </span>
</template>
<script>
export default {
  name: "SmallLoader",
  props: {
    value: {
      required: true,
    },
  },
};
</script>
