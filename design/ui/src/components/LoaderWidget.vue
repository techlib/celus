<template>
    <div :style="{height: height, color: color, paddingTop: paddingTop}" class="loader">
        <i class="fas fa-spin" :class="iconName"></i>
        <p class="text">{{ text }}</p>
    </div>
</template>
<script>
  export default {
    name: 'LoaderWidget',
    props: {
      loading: {},
      height: {default: '600px'},
      color: {default: '#1db79a88'},
      text: {default: '', required: false},
      iconName: {default: 'fa-cog'},
      paddingTop: {default: '160px'},
    }
  }
</script>
<style scoped lang="scss">

    div.loader {
        text-align: center;

        i {
            font-size: 60px;
        }

        p.text {
            margin-top: 1rem;
        }

    }

</style>
