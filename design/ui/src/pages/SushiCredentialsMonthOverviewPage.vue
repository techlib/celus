<template>
    <SushiCredentialsMonthOverviewWidget
            :organization-id="organizationId"
    />
</template>

<script>
  import SushiCredentialsMonthOverviewWidget from '@/components/sushi/SushiCredentialsMonthOverviewWidget'
  import { mapState } from 'vuex'

  export default {
    name: "SushiCredentialsMonthOverviewPage",

    components: {
      SushiCredentialsMonthOverviewWidget
    },

    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      })
    }

  }
</script>

<style lang="scss">
</style>
