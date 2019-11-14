<i18n>
en:
    maintenance: Maintenance
    no_interest: Platforms without interest definition
cs:
    maintenance: Údržba
    no_interest: Platformy bez definice zájmu
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
                <h2 v-text="$t('maintenance')"></h2>
            </v-col>
        </v-row>
        <v-row>
            <v-col :cols="12">
                <v-card>
                    <v-card-text>
                        <v-tabs v-model="tab">
                            <v-tab
                                    href="#no-interest"
                                    v-text="$t('no_interest')"
                            >
                            </v-tab>
                            <v-tab-item value="no-interest">
                                <UndefinedInterestWidget />
                            </v-tab-item>
                        </v-tabs>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>

  import UndefinedInterestWidget from '../components/UndefinedInterestWidget'
  export default {
    name: 'MaintenancePage',
    components: {
      UndefinedInterestWidget,
    },
    data () {
      return {
        tab: 'no-interest'
      }
    }
  }
</script>

<style scoped>

</style>
