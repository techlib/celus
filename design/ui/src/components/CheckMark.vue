<template>
    <v-icon small :color="value ? trueColor : falseColor" :class="extraClasses">
        {{ value ? 'fa-check' : 'fa-times' }}
    </v-icon>
</template>

<script>
  export default {
    name: 'CheckMark',
    props: {
      value: {required: true, type: Boolean},
      extraClasses: {required: false, type: String},
      trueColor: {default: 'success'},
      falseColor: {default: 'error'},
    }
  }
</script>

<style scoped>

</style>
