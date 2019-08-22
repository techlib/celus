<i18n>
en:
    short_name: Code name
    short_name_placeholder: Short code name for the report, např. UR
    name_en: Report name (English)
    name_cs: Report name (Czech)
    intro: Report type describes what kind of data is present in uploaded files.
    intro2: Reports differ significantly in the amount of detail they contain, that is the number
            of dimension (columns) the report data has. By default all reports contain support
            for the
            Title (e.g. name of the publication or database) and
            Metric (what is measured, e.g. number of visits, number of searches) columns.
            If your report data has more than these dimensions (e.g. the publisher name, etc.),
            you can add extra dimensions bellow.
    dim_short_name: Column name in file
    dim_name_en: Name to display (English)
    dim_name_cs: Name to display (Czech)
    dim_name_placeholder: How should this dimension be named in charts
    value_required: Item is required
    public_report_type: Publicly available report type
    public_report_type_tooltip: Public report types may be used by all users in all organizations.
        The opposite are organization private report types. Only admins may create public report types.

cs:
    short_name: Kódové označení
    short_name_placeholder: Krátké kódové označení reportu, např. UR
    name_en: Název reportu (anglicky)
    name_cs: Název reportu (česky)
    intro: Report type describes what kind of data is present in uploaded files.
    intro2: Reports differ significantly in the amount of detail they contain, that is the number
            of dimension (columns) the report data has. By default all reports contain support
            for the
            Title (e.g. name of the publication or database) and
            Metric (what is measured, e.g. number of visits, number of searches) columns.
            If your report data has more than these dimensions (e.g. the publisher name, etc.),
            you can add extra dimensions bellow.
    dim_short_name: Název sloupce v souboru
    dim_name_en: Zobrazované jméno (anglicky)
    dim_name_cs: Zobrazované jméno (česky)
    dim_name_placeholder: Jak se má rozměr jmenovat v grafech
    value_required: Toto pole je povinné
    public_report_type: Veřejně dostupný typ reportu
    public_report_type_tooltip: Veřejné typy reportů mohou být využity uživateli ve všech organizacích.
        Opakem jsou soukromé typy reportů dostupné pouze pro danou organizaci. Veřejné typy reportů
        mohou vytvářet pouze administrátoři.
</i18n>

<template>
    <v-form v-model="formValid" ref="form">
        <v-container>
            <v-row>
                <v-col>
                    {{ $t('intro') }}
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-text-field v-model="shortName" required :label="$t('short_name')" :placeholder="$t('short_name_placeholder')" :rules="[required]"></v-text-field>
                </v-col>
                <v-col>
                    <v-tooltip bottom max-width="500px">
                        <template v-slot:activator="{ on }">
                            <span v-on="on">
                                <v-checkbox v-model="publicReportType" :label="$t('public_report_type')"></v-checkbox>
                            </span>
                        </template>
                        <span>{{ $t('public_report_type_tooltip') }}</span>
                    </v-tooltip>

                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-text-field v-model="name_en" required :label="$t('name_en')" placeholder="e.g. Usage report"></v-text-field>
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-text-field v-model="name_cs" required :label="$t('name_cs')" placeholder="např. Report využití"></v-text-field>
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    {{ $t('intro2') }}
                </v-col>
            </v-row>
            <v-row>
                <v-col>
                    <v-container>
                        <v-row
                                v-for="(dimension, index) in selectedDimensions"
                                :key="index"
                                dense
                                align="baseline"
                        >
                            <v-col>
                                <v-select
                                        v-if="dimension.pk"
                                        v-model="selectedDimensions[index]"
                                        :items="availableDimensions"
                                        return-object
                                >
                                </v-select>
                                <v-text-field
                                        v-else
                                        v-model="selectedDimensions[index]['name']"
                                        :label="$t('dim_short_name')"
                                >
                                </v-text-field>
                            </v-col>
                            <v-col>
                                <v-text-field
                                    v-model="selectedDimensions[index]['name_cs']"
                                    :label="$t('dim_name_cs')"
                                    :readonly="!!dimension.pk"
                                    :placeholder="$t('dim_name_placeholder')"
                                >
                                </v-text-field>
                            </v-col>
                            <v-col>
                                <v-text-field
                                    v-model="selectedDimensions[index]['name_en']"
                                    :label="$t('dim_name_en')"
                                    :readonly="!!dimension.pk"
                                    :placeholder="$t('dim_name_placeholder')"
                                >
                                </v-text-field>
                            </v-col>
                            <v-col cols="auto">
                                <v-btn color="error" fab elevation="1" x-small @click="selectedDimensions.splice(index, 1)">
                                    <v-icon x-small>fa-times</v-icon>
                                </v-btn>
                            </v-col>
                        </v-row>
                        <v-row>
                            <v-col>
                                <v-btn @click="addDimension">
                                    <v-icon>fa-plus-circle</v-icon>
                                    Add dimension
                                </v-btn>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-col>
            </v-row>
            <v-row>
                <v-spacer></v-spacer>
                <v-col cols="auto">
                    <v-btn
                            @click="saveReportType()"
                            color="primary"
                            :disabled="!formValid">
                        {{ $t('save') }}
                    </v-btn>
                </v-col>
                <v-col cols="auto">
                    <slot name="extra">
                    </slot>
                </v-col>
            </v-row>
        </v-container>
    </v-form>
</template>

<script>
  import axios from 'axios'
  import { mapActions, mapState } from 'vuex'

  export default {
    name: 'ReportTypeCreateWidget',
    data () {
      return {
        shortName: '',
        name_cs: '',
        name_en: '',
        availableDimensions: [],
        selectedDimensions: [],
        savedReportType: null,
        formValid: false,
        publicReportType: false,
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
      async loadAvailableDimensions () {
        try {
          let response = await axios.get(`/api/organization/${this.organizationId}/custom-dimensions/`)
          this.availableDimensions = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error fetching dimensions: ' + error})
        }
      },
      addDimension () {
        if (this.selectedDimensions.length < 6) {
          this.selectedDimensions.push({name: '', name_cs: '', name_en: ''})
        } else {
          alert(this.$t('only_6_dimensions'))
        }
      },
      async saveReportType () {
        if (!this.formValid) {
          this.showSnackbar({content: 'Entered data is not valid', color: 'warning'})
          return
        }
        try {
          let response = await axios.post(
            `/api/organization/${this.organizationId}/report-types/`,
            {
              short_name: this.shortName,
              name_cs: this.name_cs,
              name_en: this.name_en,
              type: 2,  // text
              name: this.name_en || this.name_cs || this.shortName,
              public: this.publicReportType,
            })
          this.savedReportType = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error saving report type: ' + error, color: 'error'})
        }
      },
      required (v) {
        return !!v || this.$t('value_required')
      }
    },
    mounted () {
      this.loadAvailableDimensions()
    }
  }
</script>

<style scoped>

</style>
