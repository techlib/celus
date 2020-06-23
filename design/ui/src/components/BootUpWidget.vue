<template>
<div>
    <div class="bootup-logo">
        <img src="../assets/celus-plus-white-vertical-nobg.svg" height="158" alt="Celus Logo">
    </div>
    <h1 class="bootup">Welcome to Celus</h1>
    <LoaderWidget
        text="Loading basic data"
        height="300px"
        padding-top="80px"
        max-width="400px"
    />
</div>
</template>

<script>
  import LoaderWidget from './LoaderWidget'
  export default {
    name: 'BootUpWidget',
    components: {LoaderWidget}
  }
</script>

<style scoped lang="scss">

    h1.bootup {
        text-align: center;
        font-size: 48px;
        color: #999999;
    }

    div.bootup-logo {
        padding-top: 10vh;
        text-align: center;
    }

</style>
