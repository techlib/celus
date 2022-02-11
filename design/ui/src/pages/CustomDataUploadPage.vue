<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml">
en:
  data_file: Data file to upload
  data_file_placeholder: Upload a file with tabular data in CSV format
  error: Error
  dismiss: Dismiss
  step1: Data upload
  step2: Check before data import
  step3: Imported data view
  input_rows: Read input data rows
  output_logs: Generated logs
  imported_months: Data found for months
  overview: Overview
  upload: Upload
  add_report_type: Add new report type
  tab_chart: Chart
  tab_data: Data
  import: Import
  thats_all: That is all. The data were imported.
  return_to_platform: Go to platform page
  upload_more_files: Upload more files
  following_error_found: The following error was found when checking the imported data
  back_to_start: Back to data upload
  no_report_types: There are not reports defined for this platform - contact administrators to add some
  please_select_organization: It is necessary to select an organization before uploading data.
  requires_utf8: It seems that the provided file uses unsupported encoding. Please check that the file is encoded using UTF-8.
  clashing_import_batches_title: Can't import data
  clashing_import_batches_text: Imported file contains data for dates for which there already are existing records in the database. To import this file you need to delete the existing data first.
  delete_existing: Delete existing

cs:
  data_file: Datový soubor k nahrání
  data_file_placeholder: Nahrajte soubor s tabulkovými daty ve formátu CSV
  error: Chyba
  dismiss: Zavřít
  step1: Nahrání dat
  step2: Kontrola před importem
  step3: Zobrazení importovaných dat
  input_rows: Načtené datové řádky
  output_logs: Vygenerované záznamy
  imported_months: Data nalezena pro měsíce
  overview: Přehled
  upload: Nahrát
  add_report_type: Vytvořit nový typ reportu
  tab_chart: Graf
  tab_data: Data
  import: Importovat
  thats_all: To je vše. Data byla úspěšně importována.
  return_to_platform: Přejít na stránku platformy
  upload_more_files: Nahrát další data
  following_error_found: Při kontrole dat byla nalezena následující chyba
  back_to_start: Zpět na nahrání dat
  no_report_types: Pro tuto platformu nejsou definovány žádné reporty - kontaktujte administrátory pro jejich přidání
  please_select_organization: Pro nahrání dat je potřeba nejprve vybrat organizaci.
  requires_utf8: Zdá se, že nahraný soubor obsahuje nepodorované kódování. Prosím ověřte, že je soubor zakódován pomocí UTF-8.
  clashing_import_batches_title: Není možné naimportovat data
  clashing_import_batches_text: Nahrávaný soubor obsahuje data za období, pro které jsou již v databázi uložena data. Pro nahrání souboru je třeba nejprve existující data smazat.
  delete_existing: Smazat existující
</i18n>

<template>
  <div>
    <v-container fluid>
      <v-row>
        <v-breadcrumbs :items="breadcrumbs" class="pl-0">
          <template v-slot:item="props">
            <router-link
              v-if="props.item.linkName"
              :to="{ name: props.item.linkName, params: props.item.linkParams }"
            >
              {{ props.item.text }}
            </router-link>
            <span v-else>
              {{ props.item.text }}
            </span>
          </template>
        </v-breadcrumbs>
      </v-row>
      <v-row>
        <v-col>
          <h2 v-if="platform">{{ platform.name }}</h2>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <CustomUploadInfoWidget />
        </v-col>
      </v-row>
    </v-container>
    <v-stepper v-model="step" vertical>
      <v-stepper-step step="1" :complete="step > 1">
        {{ $t("step1") }}
      </v-stepper-step>
      <v-stepper-content step="1">
        <v-form ref="form" v-model="valid">
          <v-container fluid elevation-3 pa-5>
            <v-row no-gutters>
              <v-col cols="12">
                <ReportTypeInfoWidget
                  v-if="selectedReportType"
                  :report-type="selectedReportType"
                />
                <v-alert type="warning" v-else-if="reportTypesFetched">
                  {{ $t("no_report_types") }}
                </v-alert>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="selectedReportType"
                  :items="reportTypes"
                  item-text="name"
                  item-value="pk"
                  required
                  return-object
                  :label="$t('labels.report_type')"
                  :no-data-text="$t('no_report_types')"
                  :rules="[filledIn]"
                >
                  <template v-slot:item="{ item }">
                    <v-tooltip bottom max-width="600px" v-if="badge(item)">
                      <template #activator="{ on }">
                        <span>{{ item.name }}</span>
                        <v-badge
                          inline
                          :content="$t(badge(item).content)"
                          :color="badge(item).color"
                        >
                          <template v-slot:badge>
                            <span v-on="on">{{ $t(badge(item).content) }}</span>
                          </template>
                        </v-badge>
                      </template>
                      <span>{{ $t(badge(item).tooltip) }}</span>
                    </v-tooltip>
                    <span v-else>
                      {{ item.name }}
                    </span>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-file-input
                  v-model="dataFile"
                  prepend-icon="fa-table"
                  show-size
                  :label="$t('data_file')"
                  :placeholder="$t('data_file_placeholder')"
                  required
                  :rules="[filledIn]"
                  :disabled="!selectedReportType"
                >
                </v-file-input>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <v-btn
                  @click="postData"
                  :disabled="!valid || !$store.getters.organizationSelected"
                  class="mb-4 mr-4"
                  >{{ $t("upload") }}</v-btn
                >
                <v-alert
                  type="warning"
                  class="d-inline-block"
                  v-if="!$store.getters.organizationSelected"
                >
                  {{ $t("please_select_organization") }}
                </v-alert>
              </v-col>
            </v-row>
          </v-container>
        </v-form>
      </v-stepper-content>

      <v-stepper-step step="2" :complete="step > 2">
        {{ $t("step2") }}
      </v-stepper-step>
      <v-stepper-content step="2">
        <v-card>
          <v-card-title>{{ $t("overview") }}</v-card-title>
          <v-card-text>
            <ImportPreflightDataWidget
              v-if="preflightData"
              :preflight-data="preflightData"
              :interest-metrics="selectedInterestMetrics"
            />
            <v-alert v-else-if="preflightError" type="error">
              <strong v-text="$t('following_error_found')"></strong>:
              <span
                v-if="preflightError.kind == 'unicode-decode'"
                v-text="$t('requires_utf8')"
              >
              </span>
              <span v-else v-text="preflightError.error"></span>
            </v-alert>
            <LargeSpinner v-else />
            <v-alert
              v-if="preflightData && preflightData.clashing_months.length"
              type="warning"
              class="mt-2 mb-1"
            >
              <strong v-text="$t('clashing_import_batches_title')"></strong>:
              <span v-text="$t('clashing_import_batches_text')"></span>
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn
              v-if="preflightData && preflightData.clashing_months.length"
              color="warning"
              @click="showConfirmDeleteDialog = true"
            >
              <v-icon small class="pr-2">fa fa-trash-alt</v-icon>
              {{ $t("delete_existing") }}
            </v-btn>
            <v-btn
              v-if="preflightData && !preflightError"
              @click="processUploadObject()"
              color="primary"
              :loading="uploadObjectProcessing"
              :disabled="
                preflightData && !!preflightData.clashing_months.length
              "
              >{{ $t("import") }}</v-btn
            >
            <v-btn
              @click="backToStart()"
              v-text="$t('back_to_start')"
              color="secondary"
            ></v-btn>
          </v-card-actions>
        </v-card>
      </v-stepper-content>

      <v-stepper-step step="3" :complete="step > 3">
        {{ $t("step3") }}
      </v-stepper-step>
      <v-stepper-content step="3">
        <v-card>
          <v-card-text v-if="uploadObject && uploadObject.is_processed">
            <v-tabs v-model="tab" dark background-color="primary" fixed-tabs>
              <v-tab href="#chart">{{ $t("tab_chart") }}</v-tab>
              <v-tab href="#data">{{ $t("tab_data") }}</v-tab>
            </v-tabs>
            <v-tabs-items v-model="tab">
              <v-tab-item value="chart">
                <MDUChart :mdu-id="uploadObject.pk" />
              </v-tab-item>
              <v-tab-item value="data">
                <AccessLogList :mdu-id="uploadObject.pk" />
              </v-tab-item>
            </v-tabs-items>
            <v-container fluid>
              <v-row>
                <v-col cols="auto" class="align-self-center">
                  <v-icon color="success" small>fa fa-check-circle</v-icon>
                  {{ $t("thats_all") }}
                </v-col>
                <v-spacer></v-spacer>
                <v-col cols="auto">
                  <v-btn
                    :to="{
                      name: 'platform-detail',
                      params: { platformId: platformId },
                    }"
                    color="secondary"
                  >
                    {{ $t("return_to_platform") }}
                  </v-btn>
                </v-col>
                <v-col cols="auto">
                  <v-btn
                    @click="backToStart()"
                    v-text="$t('upload_more_files')"
                    color="primary"
                  ></v-btn>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-text v-else>
            <LargeSpinner />
          </v-card-text>
        </v-card>
      </v-stepper-content>
    </v-stepper>
    <v-dialog max-width="1100px" v-model="showConfirmDeleteDialog">
      <ImportBatchesDeleteConfirm
        v-model="showConfirmDeleteDialog"
        v-if="showConfirmDeleteDialog"
        :slices="slicesToDelete"
        @cancel="showConfirmDeleteDialog = false"
        @deleted="deletePerformed()"
      />
    </v-dialog>
    <v-dialog v-model="showErrorDialog" max-width="640px">
      <v-card class="pa-3">
        <v-card-title>{{ $t("error") }}</v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item v-for="(error, index) in errors" :key="index">
              <v-list-item-avatar>
                <v-icon color="error">fa-exclamation-circle</v-icon>
              </v-list-item-avatar>
              <v-list-item-content>{{ error }}</v-list-item-content>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showErrorDialog = false">{{ $t("dismiss") }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showAddReportTypeDialog" max-width="880px">
      <v-card class="pa-3">
        <v-card-title>{{ $t("add_report_type") }}</v-card-title>
        <v-card-text>
          <ReportTypeCreateWidget>
            <template v-slot:extra="props">
              <v-btn @click="showAddReportTypeDialog = false">{{
                $t("dismiss")
              }}</v-btn>
            </template>
          </ReportTypeCreateWidget>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions, mapState } from "vuex";
import AccessLogList from "@/components/AccessLogList";
import ReportTypeCreateWidget from "@/components/ReportTypeCreateWidget";
import LargeSpinner from "@/components/util/LargeSpinner";
import CustomUploadInfoWidget from "@/components/CustomUploadInfoWidget";
import ReportTypeInfoWidget from "@/components/ReportTypeInfoWidget";
import ImportBatchesDeleteConfirm from "@/components/ImportBatchesDeleteConfirm";
import ImportPreflightDataWidget from "@/components/ImportPreflightDataWidget";
import { badge } from "@/libs/sources.js";
import MDUChart from "@/components/MDUChart";

export default {
  name: "CustomDataUploadPage",
  components: {
    MDUChart,
    ImportBatchesDeleteConfirm,
    ImportPreflightDataWidget,
    LargeSpinner,
    ReportTypeCreateWidget,
    AccessLogList,
    CustomUploadInfoWidget,
    ReportTypeInfoWidget,
  },
  props: {
    platformId: { required: true },
    uploadObjectId: { required: false },
  },
  data() {
    return {
      dataFile: null,
      valid: false,
      platform: null,
      reportTypes: [],
      selectedReportType: null,
      showErrorDialog: false,
      showConfirmDeleteDialog: false,
      errors: [],
      step: 1,
      uploadObject: null,
      preflightData: null,
      preflightError: null,
      importStats: null,
      showAddReportTypeDialog: false,
      tab: "chart",
      uploadObjectProcessing: false,
      reportTypesFetched: false,
      deleting: false,
    };
  },
  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    breadcrumbs() {
      return [
        {
          text: this.$t("pages.platforms"),
          linkName: "platform-list",
        },
        {
          text: this.platform === null ? "" : this.platform.name,
          linkName: "platform-detail",
          linkParams: {
            platformId: this.platformId,
          },
        },
        {
          text: this.$t("actions.upload_custom_data"),
        },
      ];
    },
    selectedInterestMetrics() {
      if (this.selectedReportType) {
        return this.selectedReportType.interest_metric_set.map(
          (item) => item.metric.short_name
        );
      }
      return [];
    },
    slicesToDelete() {
      if (
        this.preflightData &&
        this.platformId &&
        this.organizationId &&
        this.uploadObject
      ) {
        return [
          {
            platform: this.platformId,
            organization: this.organizationId,
            report_type: this.uploadObject.report_type,
            months: this.preflightData.clashing_months,
          },
        ];
      }
      return [];
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    badge(item) {
      return badge(item);
    },
    async postData() {
      let formData = new FormData();
      formData.append("data_file", this.dataFile);
      formData.append("organization", this.organizationId);
      formData.append("platform", this.platformId);
      formData.append("report_type", this.selectedReportType.pk);
      try {
        let response = await axios.post("/api/manual-data-upload/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        // this.showSnackbar({content: 'Data successfully sent', color: 'success'})
        this.uploadObject = response.data;
        this.step = 2;
        await this.$router.push({
          name: "platform-upload-data-step2",
          params: {
            uploadObjectId: this.uploadObject.pk,
            platformId: this.platformId,
          },
        });
      } catch (error) {
        if (error.response && error.response.status === 400) {
          let info = error.response.data;
          if ("data_file" in info) {
            // this.showSnackbar({content: 'Data file error: ' + info.data_file[0], color: 'error'})
            this.showErrorDialog = true;
            this.errors = info.data_file;
          }
        } else {
          this.showSnackbar({ content: "Error sending data: " + error });
        }
      }
    },
    async loadPlatform() {
      if (this.organizationId) {
        try {
          let response = await axios.get(
            `/api/organization/${this.organizationId}/all-platform/${this.platformId}/`
          );
          this.platform = response.data;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading platform details: " + error,
          });
        }
      }
    },
    async loadReportTypes() {
      let url = `/api/organization/${this.organizationId}/all-platform/${this.platformId}/report-types/`;
      if (url) {
        try {
          const response = await axios.get(url);
          this.reportTypes = response.data.sort((a, b) =>
            a.name.localeCompare(b.name)
          );
          if (this.reportTypes.length > 0) {
            this.selectedReportType = this.reportTypes[0];
          }
          this.reportTypesFetched = true;
        } catch (error) {
          this.showSnackbar({ content: "Error loading title: " + error });
        }
      }
    },
    async loadPreflightData() {
      if (this.uploadObject) {
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/preflight/`;
        try {
          const response = await axios.get(url);
          this.preflightData = response.data;
          this.preflightError = null;
        } catch (error) {
          if (
            error.response &&
            error.response.status === 400 &&
            "error" in error.response.data
          ) {
            this.preflightError = error.response.data;
          } else {
            this.showSnackbar({
              content: "Error loading preflight data: " + error,
            });
          }
        }
      }
    },
    async processUploadObject() {
      this.uploadObjectProcessing = true;
      if (this.uploadObject) {
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/process/`;
        try {
          const response = await axios.post(url, {});
          this.importStats = response.data.stats;
          this.step = 3;
        } catch (error) {
          this.showSnackbar({ content: "Error processing data: " + error });
        } finally {
          this.uploadObjectProcessing = false;
        }
        // plan reloading of the object
        this.loadUploadObject();
      }
    },
    async loadUploadObject() {
      if (this.uploadObjectId) {
        try {
          let response = await axios.get(
            `/api/manual-data-upload/${this.uploadObjectId}/`
          );
          this.uploadObject = response.data;
          if (this.uploadObject.is_processed) {
            this.step = 3;
          } else {
            this.step = 2;
            this.loadPreflightData();
          }
        } catch (error) {
          this.showSnackbar({ content: "Error loading upload data: " + error });
        }
      }
    },
    filledIn(v) {
      if (v === null) return "File must be filled in";
      return true;
    },
    async backToStart() {
      this.uploadObject = null;
      await this.$router.replace({
        name: "platform-upload-data",
        params: {
          platformId: this.platformId,
        },
      });
    },
    deletePerformed() {
      this.showConfirmDeleteDialog = false;
      // update preflight data on the page
      this.loadPreflightData();
    },
  },
  mounted() {
    this.loadReportTypes();
    this.loadPlatform();
    if (this.uploadObjectId) {
      this.loadUploadObject();
    }
  },
  watch: {
    showAddReportTypeDialog() {
      this.loadReportTypes();
    },
  },
};
</script>
