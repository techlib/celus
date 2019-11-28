<i18n lang="yaml">
en:
    heatmap: Interest heatmap
cs:
    heatmap: Heatmapa zájmu
</i18n>

<template>
    <v-container fluid>
        <v-row>
            <v-col :cols="12">
                <OrganizationPlatformInterestHeatmap>
                    <h2 v-text="$t('heatmap')"></h2>
                </OrganizationPlatformInterestHeatmap>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import OrganizationPlatformInterestHeatmap
    from '../components/OrganizationPlatformInterestHeatmap'
  export default {
    name: 'OrganizationPlatformInterestOverviewPage',
    components: {
      OrganizationPlatformInterestHeatmap,
    },
  }
</script>

<style scoped>

</style>
