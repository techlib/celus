<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sources.yaml"></i18n>
<i18n lang="yaml">
en:
  data_file: Data file to upload
  data_file_placeholder: Upload a file containing data.
  error: Error
  dismiss: Dismiss
  step1: Data upload
  step2: Check before data import
  step3: Imported data view
  input_rows: Read input data rows
  overview: Overview
  upload: Upload
  add_report_type: Add new report type
  tab_chart: Chart
  tab_data: Data
  import: Import
  thats_all: That is all. The data were imported.
  return_to_platform: Go to platform page
  upload_more_files: Upload more files
  preflight_error_found: Error occured during data check
  import_error_found: The following error was found when data were imported
  back_to_start: Back to data upload
  no_report_types: There are not reports defined for this platform - contact administrators to add some
  please_select_organization: It is necessary to select an organization before uploading data.
  clashing_import_batches_title: Can't import data
  clashing_import_batches_text: Imported file contains data for dates for which there already are existing records in the database. To import this file you need to delete the existing data first.
  delete_existing: Delete existing
  regenerate_preflight: Regenerate overview
  preflight_data_outdated: Preflight data are outdated, please regenerate preflight.
  errors:
    requires_utf8: It seems that the provided file uses unsupported encoding. Please check that the file is encoded using UTF-8.
    unknown_preflight_error: An unknown error has occured during data check.
    unknown_import_error: An unknown error has occured during data import.

cs:
  data_file: Datový soubor k nahrání
  data_file_placeholder: Nahrajte soubor, který obsahuje data.
  error: Chyba
  dismiss: Zavřít
  step1: Nahrání dat
  step2: Kontrola před importem
  step3: Zobrazení importovaných dat
  input_rows: Načtené datové řádky
  overview: Přehled
  upload: Nahrát
  add_report_type: Vytvořit nový typ reportu
  tab_chart: Graf
  tab_data: Data
  import: Importovat
  thats_all: To je vše. Data byla úspěšně importována.
  return_to_platform: Přejít na stránku platformy
  upload_more_files: Nahrát další data
  preflight_error_found: Chyba při kontrole dat
  import_error_found: Při nahrávání dat byla nalezena následující chyba
  back_to_start: Zpět na nahrání dat
  no_report_types: Pro tuto platformu nejsou definovány žádné reporty - kontaktujte administrátory pro jejich přidání
  please_select_organization: Pro nahrání dat je potřeba nejprve vybrat organizaci.
  clashing_import_batches_title: Není možné naimportovat data
  clashing_import_batches_text: Nahrávaný soubor obsahuje data za období, pro které jsou již v databázi uložena data. Pro nahrání souboru je třeba nejprve existující data smazat.
  delete_existing: Smazat existující
  regenerate_preflight: Přegenerovat přehled
  preflight_data_outdated: Data přehledu již nejsou platná. Prosím přegenerujte přehled.
  errors:
    requires_utf8: Zdá se, že nahraný soubor obsahuje nepodorované kódování. Prosím ověřte, že je soubor zakódován pomocí UTF-8.
    unknown_preflight_error: Během kontroly dat se vyskytla neznámá chyba.
    unknown_import_error: Během importu dat se vyskytla neznámá chyba.
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
    <v-sheet
      v-if="globalSpinnerOn"
      class="justify-center"
      elevation="1"
      width="100%"
    >
      <v-skeleton-loader
        type="list-item-avatar-three-line, list-item-avatar-three-line, list-item-avatar-three-line"
      />
    </v-sheet>
    <v-stepper v-model="step" v-else vertical>
      <v-stepper-step step="1" :complete="!!uploadObjectId || step > 1">
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
                  :loading="!reportTypesFetched"
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
              <v-col class="d-flex align-center">
                <v-btn
                  @click="postData"
                  :disabled="!valid || !$store.getters.organizationSelected"
                  :loading="uploading"
                  >{{ $t("upload") }}</v-btn
                >
                <v-progress-linear
                  class="ma-3"
                  v-model="uploadProgress"
                  round
                  v-if="uploading"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-alert
                type="warning"
                class="d-inline-block"
                v-if="!$store.getters.organizationSelected"
              >
                {{ $t("please_select_organization") }}
              </v-alert>
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
            <LargeSpinner v-if="state == 'initial' || spinnerOn || !state" />
            <v-alert
              v-else-if="state == 'preflight' && !preflightDataFormatValid"
              type="warning"
            >
              <span v-text="$t('preflight_data_outdated')"></span>
            </v-alert>
            <ImportPreflightDataWidget
              v-else-if="state == 'preflight'"
              :preflight-data="preflightData"
              :interest-metrics="selectedInterestMetrics"
              :usable-metrics="usableMetrics"
              :check-metrics="checkMetrics"
              :auto-create-metrics="automaticallyCreateMetrics"
              :metrics="metrics"
            />
            <v-alert v-else-if="state == 'prefailed'" type="error">
              <h3 v-text="$t('preflight_error_found')" class="pb-2"></h3>
              <strong v-if="error == 'unicode-decode'">
                {{ $t("errors.requires_utf8") }}
              </strong>
              <strong v-else>
                {{ $t("errors.unknown_preflight_error") }}
              </strong>
              <pre
                v-text="errorDetails.exception"
                v-if="errorDetails && errorDetails.exception"
                class="pt-2"
              ></pre>
            </v-alert>
            <v-alert
              v-else-if="preflightData && preflightData.clashing_months.length"
              type="warning"
              class="mt-2 mb-1"
            >
              <strong v-text="$t('clashing_import_batches_title')"></strong>:
              <span v-text="$t('clashing_import_batches_text')"></span>
            </v-alert>
          </v-card-text>
          <v-card-actions v-if="state == 'preflight'">
            <v-btn
              v-if="
                preflightData &&
                preflightDataFormatValid &&
                preflightData.clashing_months.length
              "
              color="warning"
              @click="showConfirmDeleteDialog = true"
            >
              <v-icon small class="pr-2">fa fa-trash-alt</v-icon>
              {{ $t("delete_existing") }}
            </v-btn>
            <v-btn
              v-if="canImport"
              @click="triggerImportData()"
              color="success"
              :loading="state == 'importing' || importing"
              :disabled="
                (preflightData && !!preflightData.clashing_months.length) ||
                preflighting
              "
            >
              <v-icon small class="pr-2">fas fa-cogs</v-icon>
              {{ $t("import") }}
            </v-btn>
            <v-btn
              @click="backToStart()"
              v-text="$t('back_to_start')"
              color="secondary"
            ></v-btn>
          </v-card-actions>
          <v-card-actions v-else-if="state == 'prefailed'">
            <v-btn
              color="primary"
              @click="regeneratePreflight"
              :disabled="importing"
            >
              <v-icon small class="pr-2">fas fa-redo</v-icon>
              {{ $t("regenerate_preflight") }}
            </v-btn>
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
          <v-card-text v-if="state == 'imported'">
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
          <v-card-text v-else-if="state == 'failed'">
            <v-container>
              <v-row>
                <v-col cols="auto">
                  <v-alert type="error">
                    <h3 v-text="$t('import_error_found')" class="pb-2"></h3>
                    <strong>{{ $t("unknown_import_error") }}</strong>
                    <pre
                      v-text="errorDetails.exception"
                      v-if="errorDetails && errorDetails.exception"
                      class="pt-2"
                    ></pre>
                  </v-alert>
                </v-col>
              </v-row>
              <v-row>
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
        :import-batch-slices="slicesToDelete"
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
import { mapActions, mapGetters, mapState } from "vuex";
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
      reportTypesFetched: false,
      metrics: [],
      metricsFetched: false,
      selectedReportType: null,
      showErrorDialog: false,
      showConfirmDeleteDialog: false,
      errors: [],
      step: 1,
      uploadObject: null,
      showAddReportTypeDialog: false,
      tab: "chart",
      deleting: false,
      refreshTimeout: null,
      spinnerOn: false,
      globalSpinnerOn: true,
      uploading: false,
      importing: false,
      preflighting: false,
      uploadProgress: 0,
    };
  },
  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      automaticallyCreateMetrics: "automaticallyCreateMetrics",
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
      if (this.uploadObject && this.uploadObject.report_type) {
        return this.uploadObject.report_type.interest_metric_set.map(
          (item) => item.metric.short_name
        );
      }
      return [];
    },
    usableMetrics() {
      if (this.uploadObject && this.uploadObject.report_type) {
        if (this.uploadObject.report_type.controlled_metrics) {
          return this.metrics
            .filter((metric) =>
              this.uploadObject.report_type.controlled_metrics.includes(
                metric.pk
              )
            )
            .map((item) => item.short_name);
        } else {
          return this.metrics.map((metric) => metric.short_name);
        }
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
            report_type: this.uploadObject.report_type.pk,
            months: this.preflightData.clashing_months,
          },
        ];
      }
      return [];
    },
    errorDetails() {
      if (this.uploadObject) {
        return this.uploadObject.error_details;
      } else {
        return null;
      }
    },
    canImport() {
      if (this.uploadObject) {
        return this.uploadObject.can_import;
      } else {
        return false; // not uploaded yet
      }
    },
    error() {
      if (this.uploadObject) {
        return this.uploadObject.error;
      } else {
        return null;
      }
    },
    state() {
      if (this.uploadObject) {
        return this.uploadObject.state;
      } else {
        return null;
      }
    },
    preflightDataFormatValid() {
      if (this.uploadObject) {
        return this.uploadObject.preflight.format_version === "2";
      } else {
        return false;
      }
    },
    checkMetrics() {
      if (this.uploadObject) {
        return this.uploadObject.report_type.controlled_metrics.length > 0;
      } else {
        return false;
      }
    },
    preflightData() {
      if (this.uploadObject) {
        let result = JSON.parse(JSON.stringify(this.uploadObject.preflight));
        result.clashing_months = this.uploadObject.clashing_months || [];
        result.can_import = this.uploadObject.can_import || false;
        return result;
      } else {
        return null;
      }
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    badge(item) {
      return badge(item);
    },
    setProgress(total, current) {
      if (total) {
        this.uploadProgress = (100 * current) / total;
      }
    },
    async postData() {
      let formData = new FormData();
      formData.append("data_file", this.dataFile);
      formData.append("organization", this.organizationId);
      formData.append("platform", this.platformId);
      formData.append("report_type_id", this.selectedReportType.pk);

      this.uploading = true;
      this.uploadProgress = 0;
      try {
        let response = await axios.post("/api/manual-data-upload/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => this.setProgress(e.total, e.loaded),
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
        if (error.response?.status === 400) {
          let info = error.response.data;
          if ("data_file" in info) {
            // this.showSnackbar({content: 'Data file error: ' + info.data_file[0], color: 'error'})
            this.showErrorDialog = true;
            this.errors = info.data_file;
          }
        } else {
          this.showSnackbar({ content: "Error sending data: " + error });
        }
      } finally {
        this.uploading = false;
        this.uploadProgress = 0;
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
            this.selectedReportType = this.reportTypes[0]; // default
            if (this.$router.currentRoute.query?.report_type_id) {
              let rt_id = parseInt(
                this.$router.currentRoute.query.report_type_id
              );
              this.selectedReportType = this.reportTypes.find(
                (rt) => rt.pk === rt_id
              );
              this.selectedReportType ??= this.reportTypes[0];
            }
          }
          this.reportTypesFetched = true;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading report types: " + error,
          });
        }
      }
    },
    async loadMetrics() {
      let url = `/api/metric/`;
      try {
        const response = await axios.get(url);
        this.metrics = response.data;
        this.metricsFetched = true;
      } catch (error) {
        this.showSnackbar({ content: "Error loading metrics: " + error });
      }
    },
    async triggerImportData() {
      if (this.uploadObject && !this.importing && this.canImport) {
        this.importing = true;
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/import-data/`;
        try {
          await axios.post(url, {});
        } catch (error) {
          this.showSnackbar({ content: "Error processing data: " + error });
        } finally {
          this.importing = false;
        }
        // reload object
        await this.loadMdu();
      }
    },
    async regeneratePreflight() {
      if (
        this.uploadObject &&
        !this.preflighting &&
        ["preflight", "prefailed"].includes(this.uploadObject.state)
      ) {
        this.preflighting = true;
        let url = `/api/manual-data-upload/${this.uploadObject.pk}/preflight/`;
        try {
          await axios.post(url, {});
        } catch (error) {
          this.showSnackbar({
            content: "Error triggering preflight generation: " + error,
          });
        } finally {
          this.preflighting = false;
        }
        // reload object
        this.spinnerOn = true;
        this.loadMdu();
      }
    },
    async loadMdu() {
      this.cancelRefreshTimeout();

      // Try to fetch metrics first
      if (!this.metricsFetched) {
        await this.loadMetrics();
      }

      if (this.uploadObjectId) {
        try {
          let response = await axios.get(
            `/api/manual-data-upload/${this.uploadObjectId}/`
          );
          this.uploadObject = response.data;
          switch (this.uploadObject.state) {
            case "initial":
            case "prefailed":
              this.step = 2;
              break;
            case "preflight":
              // Auto regenarete outdated preflights
              if (!this.preflightDataFormatValid) {
                this.regeneratePreflight();
              }
              this.step = 2;
              break;
            case "importing":
            case "imported":
            case "failed":
              this.step = 3;
              break;
          }
          if (["initial", "importing"].includes(this.uploadObject.state)) {
            this.cancelRefreshTimeout();
            this.refreshTimeout = setTimeout(() => this.loadMdu(), 5000); // every 5 seconds
          }
        } catch (error) {
          this.showSnackbar({ content: "Error loading upload data: " + error });
        } finally {
          this.spinnerOn = false;
        }
      }
    },
    cancelRefreshTimeout() {
      if (this.refreshTimeout) {
        clearTimeout(this.refreshTimeout);
        this.refreshTimeout = null;
      }
    },
    filledIn(v) {
      if (v === null) return "File must be filled in";
      return true;
    },
    async backToStart() {
      let reportTypeId = this.uploadObject.report_type;
      this.uploadObject = null;
      await this.$router.replace({
        name: "platform-upload-data",
        params: {
          platformId: this.platformId,
        },
        query: {
          report_type_id: reportTypeId,
        },
      });
    },
    deletePerformed() {
      this.showConfirmDeleteDialog = false;
      // regenerate preflight
      this.regeneratePreflight();
    },
    async loadRequiredData() {
      // report type API call is quite time consuming
      // so waiting for it to finish would be inconvenient
      // loading attribte is v-select use used instead
      this.loadReportTypes();
      await Promise.all([this.loadMetrics(), this.loadPlatform()]);
      this.globalSpinnerOn = false;
    },
  },
  mounted() {
    if (this.uploadObjectId && this.step == 1) {
      // If object is present move to step2
      this.step = 2;
    }
    this.loadRequiredData();
    if (this.uploadObjectId) {
      this.loadMdu();
    }
  },
  beforeDestroy() {
    this.cancelRefreshTimeout();
  },
  watch: {
    showAddReportTypeDialog() {
      this.loadReportTypes();
    },
  },
};
</script>
