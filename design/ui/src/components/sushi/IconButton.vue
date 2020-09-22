<template>
  <v-icon
    class="button-icon px-1"
    :disabled="disabled"
    v-on="$listeners"
    v-ripple
  >
    <slot> </slot>
  </v-icon>
</template>
<script>
export default {
  name: "IconButton",

  props: {
    disabled: { default: false, type: Boolean },
  },
};
</script>
<style lang="scss" scoped>
.button-icon {
  cursor: pointer;
}
</style>
