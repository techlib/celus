<i18n src="../locales/dialog.yaml"></i18n>
<i18n>
en:
    short_name: Column name in file
    name_en: Name to display (English)
    name_cs: Name to display (Czech)
    name_placeholder: How should this dimension be named in charts
cs:
    short_name: Název sloupce v souboru
    name_en: Zobrazované jméno (anglicky)
    name_cs: Zobrazované jméno (česky)
    name_placeholder: Jak se má rozměr jmenovat v grafech
</i18n>
<template>
    <v-form v-model="valid" ref="form">
    <v-container>
        <v-row wrap>
            <v-col cols="12" sm="6">
                <v-text-field
                        v-model="shortName"
                        :label="$t('short_name')"
                        required
                        :rules="[required]"
                ></v-text-field>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12" sm="6">
                <v-text-field
                        v-model="name_cs"
                        :label="$t('name_cs')"
                        :placeholder="$t('name_placeholder')"
                        :rules="[required]"
                ></v-text-field>
            </v-col>
            <v-col cols="12" sm="6">
                <v-text-field
                        v-model="name_en"
                        :label="$t('name_en')"
                        :placeholder="$t('name_placeholder')"
                        :rules="[required]"
                ></v-text-field>
            </v-col>
        </v-row>
        <v-row>
            <v-spacer></v-spacer>
            <v-col cols="auto">
                <v-btn
                        @click="saveDimension()"
                        :disabled="!valid"
                        color="primary"
                >
                    {{ $t('create') }}
                </v-btn>
            </v-col>
            <v-col cols="auto">
                <v-btn
                        @click="$emit('cancel')"
                >
                    {{ $t('cancel') }}
                </v-btn>
            </v-col>
        </v-row>
    </v-container>
    </v-form>
</template>

<script>
  import axios from 'axios'
  import { mapActions, mapState } from 'vuex'
  export default {
    name: 'DimensionCreateWidget',
    props: {
      public: {
        required: true,
        type: Boolean,
      }
    },
    data () {
      return {
        shortName: '',
        name_cs: '',
        name_en: '',
        valid: false,
      }
    },
    computed: {
      ...mapState({
        organizationId: 'selectedOrganizationId',
      }),
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async saveDimension () {
        try {
          let response = await axios.post(`/api/organization/${this.organizationId}/dimensions/`,
            {
              short_name: this.shortName,
              name_cs: this.name_cs,
              name_en: this.name_en,
              name: this.name_cs || this.name_en || this.shortName,
              public: this.public,
            }
          )
          this.$emit('input', response.data)
        } catch (error) {
          this.showSnackbar({content: 'Error saving dimension ' + error, color: 'error'})
        }
      },
      clearDialog () {
        this.$refs.form.reset()
        /*this.shortName = ''
        this.name_cs = ''
        this.name_en = ''*/
      },
      required (v) {
        return !!v || this.$t('value_required')
      },
    },

  }
</script>

<style scoped>

</style>
