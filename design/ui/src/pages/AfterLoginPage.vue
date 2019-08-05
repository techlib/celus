<template>
    <div></div>
</template>

<script>
  import { mapActions, mapState } from 'vuex'

  export default {
    name: 'AfterLoginPage',
    computed: {
      ...mapState({
        user: 'user',
        }),
    },
    methods: {
      ...mapActions({
        loadUserData: 'loadUserData',
      })
    },
    mounted () {
      this.loadUserData()
    },
    watch: {
      user () {
        if (this.user)
          this.$router.push({name: 'home'})
      }
    }
  }
</script>

<style scoped>

</style>
