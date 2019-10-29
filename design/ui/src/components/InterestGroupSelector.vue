<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-container fluid>
        <v-row dense>
            <v-col cols="12">
                <strong>{{ $t('interest_types') }}</strong>:
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="auto" v-for="ig in interestGroups" :key="ig.pk">
                <v-checkbox v-model="selectedGroups" class="small-checkbox" :label="ig.name" :value="ig.short_name"></v-checkbox>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import {mapActions} from 'vuex'
  import axios from 'axios'

  export default {
    name: "InterestGroupSelector",
    props: {
      value: {default: []}
    },
    data () {
      return {
        interestGroups: [],
        selectedGroups: this.value,
        loading: false,
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async fetchInterestGroups() {
        this.loading = true
        try {
          let response = await axios.get('/api/interest-groups/')
          this.interestGroups = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error loading interest groups: ' + error, color: 'error'})
        } finally {
          this.loading = false
        }
      },
    },
    created () {
      this.fetchInterestGroups()
    },
    watch: {
      selectedGroups () {
        this.$emit('input', this.selectedGroups)
      }
    }
  }
</script>

<style scoped>

</style>
