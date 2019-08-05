<template>
    <!--v-layout justify-center>
        <div v-if="!user" class="text-center ma-12">
            <v-progress-circular
                    indeterminate
                    size="100"
            ></v-progress-circular>
        </div>
        <v-dialog persistent max-width="290">
            <v-card>
                <v-card-title class="headline">Still not logged in</v-card-title>
                <v-card-text>You are not logged in. Please click Login to be redirected to login page.</v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" text href="/secure">Login</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-layout-->
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
