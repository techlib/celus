<template>
    <div :style="{height: height, color: color}" class="loader">
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
    }
  }
</script>
<style scoped lang="scss">

    div.loader {
        //background-color: white;
        text-align: center;
        padding-top: 160px;

        i {
            font-size: 60px;
            display: block;
        }

        p.text {
            margin-top: 1rem;
        }

    }

</style>
