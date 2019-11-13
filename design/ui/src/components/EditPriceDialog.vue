<template>
    <v-card>
        <v-card-text>
            <v-text-field
                    type="number"
                    v-model="newPrice"
            >
            </v-text-field>
        </v-card-text>
        <v-card-actions>
            <v-btn @click="close" color="secondary">{{ $t('cancel') }}</v-btn>
            <v-spacer></v-spacer>
            <v-btn @click="save" color="primary">{{ $t('save') }}</v-btn>
        </v-card-actions>
    </v-card>
</template>
<script>
  export default {
    name: 'EditPriceDialog',
    props: {
      price: {},
    },
    data () {
      return {
        newPrice: this.price,
      }
    },
    methods: {
      save () {
        this.$emit('save', {price: this.newPrice})
        this.close()
      },
      close () {
        this.$emit('close')
      }
    }
  }
</script>
