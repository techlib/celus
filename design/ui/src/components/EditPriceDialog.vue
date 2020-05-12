<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
    year: Year
    price: Price

cs:
    year: Rok
    price: Cena
</i18n>

<template>
    <v-card>
        <v-card-text>
            <table class="pt-4">
                <tr v-if="organization">
                    <th v-text="$t('organization')" class="text-left"></th>
                    <td v-text="organization"></td>
                </tr>
                <tr v-if="platform">
                    <th v-text="$t('platform')" class="text-left"></th>
                    <td v-text="platform"></td>
                </tr>
                <tr v-if="year">
                    <th v-text="$t('year')" class="text-left"></th>
                    <td v-text="year"></td>
                </tr>
                <tr>
                    <th v-text="$t('price')" class="text-left"></th>
                    <td>
                        <v-text-field
                                type="number"
                                v-model="newPrice"
                        >
                        </v-text-field>
                    </td>
                </tr>
            </table>
        </v-card-text>
        <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="close" color="secondary">{{ $t('cancel') }}</v-btn>
            <v-btn @click="save" color="primary">{{ $t('save') }}</v-btn>
            <v-spacer></v-spacer>
        </v-card-actions>
    </v-card>
</template>
<script>
  export default {
    name: 'EditPriceDialog',
    props: {
      price: {type: Number, required: true},
      platform: {type: String, required: false},
      organization: {type: String, required: false},
      year: {type: Number, required: false},
    },
    data () {
      return {
        newPrice: this.price,
      }
    },
    methods: {
      save () {
        this.$emit('save', {price: this.newPrice})
      },
      close () {
        this.$emit('close')
      }
    },
    watch: {
      price () {
        this.newPrice = this.price
      }
    }
  }
</script>

<style lang="scss">

    th {
        padding-right: 0.5rem;
    }

</style>
