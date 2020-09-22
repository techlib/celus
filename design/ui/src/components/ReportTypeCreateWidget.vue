<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  short_name: Code name
  short_name_placeholder: Short code name for the report, např. UR
  name_en: Report name (English)
  name_cs: Report name (Czech)
  intro: Report type describes what kind of data is present in uploaded files.
  intro2:
    Reports differ significantly in the amount of detail they contain, that is the number
    of dimension (columns) the report data has. By default all reports contain support
    for the
    Title (e.g. name of the publication or database) and
    Metric (what is measured, e.g. number of visits, number of searches) columns.
    If your report data has more than these dimensions (e.g. the publisher name, etc.),
    you can add extra dimensions bellow.
  public_report_type: Publicly available report type
  public_report_type_tooltip:
    Public report types may be used by all users in all organizations.
    The opposite are organization private report types. Only admins may create public report types.
  save: Save
  add_dimension: Add dimension
  only_6_dimensions: Only up to 6 dimensions are supported
  select_dimension: Select dimension
  create_new_dim: Create new rozměr

cs:
  short_name: Kódové označení
  short_name_placeholder: Krátké kódové označení reportu, např. UR
  name_en: Název reportu (anglicky)
  name_cs: Název reportu (česky)
  intro: Typ reportu popisuje strukturu dat a typ dat v nahrávaných souborech.
  intro2:
    Reporty se výrazně liší svou detailností, tedy počtem rozměrů (sloupců), které obsahují.
    Každý typ reportu má ve výchozím stavu podporu pro Titul (např. jméno publikace nebo
    databáze) a Metriku (co je měřeno, např. počet návštěv, počet vyhledávání, atp.).
    Pokud vaše data obsahují více než tyto rozměry (např. jméno vydavatele, atp.)
    můžete přidat další rozměry níže.
  public_report_type: Veřejně dostupný typ reportu
  public_report_type_tooltip:
    Veřejné typy reportů mohou být využity uživateli ve všech organizacích.
    Opakem jsou soukromé typy reportů dostupné pouze pro danou organizaci. Veřejné typy reportů
    mohou vytvářet pouze administrátoři.
  save: Uložit
  add_dimension: Přidat rozměr
  only_6_dimensions: Maximální podporovaný počet rozměrů je 6
  select_dimension: Vyberte rozměr
  create_new_dim: Vytvořit nový rozměr
</i18n>

<template>
  <v-form v-model="formValid" ref="form">
    <v-container>
      <v-row>
        <v-col>
          {{ $t("intro") }}
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            v-model="shortName"
            required
            :label="$t('short_name')"
            :placeholder="$t('short_name_placeholder')"
            :rules="[required]"
          ></v-text-field>
        </v-col>
        <v-col>
          <v-tooltip bottom max-width="500px">
            <template v-slot:activator="{ on }">
              <span v-on="on">
                <v-checkbox
                  v-model="publicReportType"
                  :label="$t('public_report_type')"
                ></v-checkbox>
              </span>
            </template>
            <span>{{ $t("public_report_type_tooltip") }}</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            v-model="name_en"
            required
            :label="$t('name_en')"
            placeholder="e.g. Usage report"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            v-model="name_cs"
            required
            :label="$t('name_cs')"
            placeholder="např. Report využití"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          {{ $t("intro2") }}
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
                  v-model="selectedDimensions[index]"
                  :items="availableDimensions"
                  item-text="short_name"
                  item-value="pk"
                  :label="$t('select_dimension') + ' #' + (index + 1)"
                >
                  <template v-slot:item="props">
                    {{ props.item.short_name }}: {{ props.item.name }}
                  </template>
                  <template v-slot:prepend-item>
                    <v-list-item @click="addNewDimension()">
                      <v-list-item-content>
                        <v-list-item-title>
                          <v-icon small class="mr-2">fa-plus</v-icon>
                          {{ $t("create_new_dim") }}
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                    <v-divider class="mt-2"></v-divider>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="auto">
                <v-btn
                  color="error"
                  fab
                  elevation="1"
                  x-small
                  @click="selectedDimensions.splice(index, 1)"
                >
                  <v-icon x-small>fa-times</v-icon>
                </v-btn>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <v-btn @click="addDimension">
                  <v-icon class="mr-2">fa-plus-circle</v-icon>
                  {{ $t("add_dimension") }}
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-col>
      </v-row>
      <v-row>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-btn @click="showHelpDialog = true" color="secondary">
            <v-icon small class="mr-2">far fa-question-circle</v-icon>
            {{ $t("help") }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn
            @click="saveReportType()"
            color="primary"
            :disabled="!formValid"
          >
            {{ $t("save") }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <slot name="extra"> </slot>
        </v-col>
      </v-row>
    </v-container>
    <v-dialog v-model="showAddDimensionDialog" max-width="640px">
      <v-card>
        <v-card-title>{{ $t("create_new_dim") }}</v-card-title>
        <v-card-text>
          <DimensionCreateWidget
            :public="publicReportType"
            @input="newDimensionCreated(value)"
            @cancel="showAddDimensionDialog = false"
            ref="dimWidget"
          >
          </DimensionCreateWidget>
        </v-card-text>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showHelpDialog" max-width="800px">
      <ReportTypeExamples @close="showHelpDialog = false" />
    </v-dialog>
  </v-form>
</template>

<script>
import axios from "axios";
import { mapActions, mapState } from "vuex";
import DimensionCreateWidget from "./DimensionCreateWidget";
import ReportTypeExamples from "./ReportTypeExamples";

export default {
  name: "ReportTypeCreateWidget",
  components: { DimensionCreateWidget, ReportTypeExamples },
  data() {
    return {
      shortName: "",
      name_cs: "",
      name_en: "",
      allDimensions: [],
      selectedDimensions: [],
      savedReportType: null,
      formValid: false,
      publicReportType: false,
      showAddDimensionDialog: false,
      showHelpDialog: false,
    };
  },
  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    availableDimensions() {
      return this.allDimensions.filter(
        (item) => item.public === this.publicReportType
      );
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadAvailableDimensions() {
      try {
        let response = await axios.get(
          `/api/organization/${this.organizationId}/dimensions/`
        );
        this.allDimensions = response.data;
      } catch (error) {
        this.showSnackbar({ content: "Error fetching dimensions: " + error });
      }
    },
    addDimension() {
      if (this.selectedDimensions.length < 6) {
        this.selectedDimensions.push({
          short_name: "",
          name_cs: "",
          name_en: "",
        });
      } else {
        alert(this.$t("only_6_dimensions"));
      }
    },
    async saveReportType() {
      if (!this.formValid) {
        this.showSnackbar({
          content: "Entered data is not valid",
          color: "warning",
        });
        return;
      }
      try {
        let response = await axios.post(
          `/api/organization/${this.organizationId}/report-types/`,
          {
            short_name: this.shortName,
            name_cs: this.name_cs,
            name_en: this.name_en,
            type: 2, // text
            name: this.name_en || this.name_cs || this.shortName,
            public: this.publicReportType,
            dimensions: this.selectedDimensions,
          }
        );
        this.savedReportType = response.data;
      } catch (error) {
        if (error.response && error.response.status === 400) {
          let info = error.response.data;
          let error_msg = "";
          if (info.index("non_field_errors") >= 0) {
            error_msg = info.non_field_errors;
          } else {
            for (let [key, value] of Object.entries(info)) {
              error_msg += `${key}: ${value}; `;
            }
          }
          this.showSnackbar({
            content: "Error saving report type: " + error_msg,
            color: "error",
          });
        } else {
          this.showSnackbar({
            content: "Error saving report type: " + error,
            color: "error",
          });
        }
      }
    },
    required(v) {
      return !!v || this.$t("value_required");
    },
    addNewDimension() {
      if (this.$refs.dimWidget) this.$refs.dimWidget.clearDialog();
      this.showAddDimensionDialog = true;
    },
    async newDimensionCreated(value) {
      console.log(value);
      this.showAddDimensionDialog = false;
      this.loadAvailableDimensions();
    },
  },
  mounted() {
    this.loadAvailableDimensions();
  },
};
</script>

<style scoped></style>
