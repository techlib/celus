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
  import {mapActions, mapState} from 'vuex'

  export default {
    name: "InterestGroupSelector",
    data () {
      return {
        loading: false,
      }
    },
    computed: {
      ...mapState({
        interestGroups: state => state.interest.interestGroups,
        selectedGroupsStore: state => state.interest.selectedGroups,
      }),
      selectedGroups: {
        get: function () {return this.selectedGroupsStore},
        set: function (value) {
          this.changeSelectedGroups(value)
        }
      }
    },
    methods: {
      ...mapActions({
        changeSelectedGroups: 'changeSelectedGroups',
      })
    }
  }
</script>

<style scoped>

</style>
