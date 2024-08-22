<template>
  <a
    :href="`https://doi.org/${doi}`"
    target="_blank"
    rel="noopener noreferrer"
    :class="small ? 'caption' : ''"
  >
    {{ doi }}
    <v-icon :x-small="small" :small="!small" class="ps-1"
      >fa-external-link-alt</v-icon
    >
  </a>
</template>

<script>
export default {
  name: "DoiLink",

  props: {
    doi: { type: String, required: true },
    small: { type: Boolean, default: false },
  },
};
</script>

<style scoped lang="scss"></style>
