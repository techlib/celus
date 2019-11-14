<i18n>
en:
    maintenance: Maintenance
cs:
    maintenance: Údržba
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
                <h2 v-text="$t('maintenance')"></h2>
            </v-col>
        </v-row>
        <v-row>
            <UndefinedInterestWidget />
        </v-row>
    </v-container>
</template>

<script>

  import UndefinedInterestWidget from '../components/UndefinedInterestWidget'
  export default {
    name: 'MaintenancePage',
    components: {
      UndefinedInterestWidget,
    }
  }
</script>

<style scoped>

</style>
