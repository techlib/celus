<template>
    <div :style="{'height': height}" class="loader">
        <i class="fas fa-cog fa-spin" :style="{color: color}"></i>
    </div>
</template>
<script>
  export default {
    name: 'LoaderWidget',
    props: {
      loading: {},
      height: {default: '600px'},
      color: {default: '#1db79a88'},
    }
  }
</script>
<style scoped lang="scss">

    div.loader {
        //background-color: white;
        font-size: 60px;
        text-align: center;

        i {
            margin-top: 160px;
        }

    }

</style>
