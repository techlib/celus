<template>
    <v-icon small :color="value ? 'success' : 'error'" :class="extraClasses">
        {{ value ? 'fa-check' : 'fa-times' }}
    </v-icon>
</template>

<script>
  export default {
    name: 'CheckMark',
    props: {
      value: {required: true, type: Boolean},
      extraClasses: {required: false, type: String},
    }
  }
</script>

<style scoped>

</style>
