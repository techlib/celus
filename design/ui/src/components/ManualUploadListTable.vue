<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  state: State
  delete_warning:
    You are about to delete this manually uploaded data from the database.
    Please confirm this action.
  delete_success: Successfully deleted selected manually uploaded data
  mdu_page: To processing page
  no_data: There are no manually uploaded data yet
  data_file: Data file
  data_file_tt: Download a copy of the file that was uploaded

cs:
  state: Stav
  delete_warning: Prosím potvrďte, že chcete smazat z databáze tato ručně nahraná data.
  delete_success: Vybraná ručně nahraná data byla úspěšně smazána
  mdu_page: Na stránku zpracování
  no_data: Zatím nebyla ručně nahrána žádná data
  data_file: Soubor s daty
  data_file_tt: Stáhněte si kopii souboru, který byl nahrán
</i18n>

<template>
  <v-card>
    <v-card-text>
      <v-container fluid class="pt-0 px-0 px-sm-2">
        <v-row>
          <v-spacer></v-spacer>
          <v-col md="4" cols="12">
            <v-autocomplete
              v-model="filterPlatforms"
              :label="$t('title_fields.platforms')"
              :items="filteredPlatforms"
              item-value="pk"
              item-title="name"
              multiple
              clearable
              clear-icon="fas fa-times"
            ></v-autocomplete>
          </v-col>
          <v-col md="4" cols="12">
            <v-autocomplete
              v-model="filterReportTypes"
              :label="$t('title_fields.report_types')"
              :items="filteredReportTypes"
              item-value="pk"
              :item-title="(item) => item.name"
              multiple
              clearable
              clear-icon="fas fa-times"
            ></v-autocomplete>
          </v-col>
          <v-col md="4" cols="12">
            <v-text-field
              v-model="searchDebounced"
              append-inner-icon="fa fa-search"
              :label="$t('labels.search')"
              single-line
              hide-details
              clearable
              clear-icon="fas fa-times"
            >
            </v-text-field>
          </v-col>
        </v-row>
      </v-container>
      <v-data-table-server
        :items="mdusProcessed"
        :headers="headers"
        :no-data-text="$t('no_data')"
        :loading="loading"
        v-model:sort-by="orderByCr"
        :items-length="mduCount"
        v-model:page="page"
        v-model:items-per-page="pageSize"
        :search="searchDebounced"
        :items-per-page-options="[10, 25, 50]"
      >
        <!-- v-model:sort-by="orderByCr" -->
        <template #headers="{ columns }">
          <TableCustomSort
            :columns="columns"
            v-model:externalOrderBy="orderByCr"
          />
        </template>
        <template #item.user.last_name="{ item }">
          {{ userToString(item.user) }}
        </template>
        <template #item.created="{ item }">
          <span v-html="isoDateTimeFormatSpans(item.created)"></span>
        </template>
        <template #item.report_type.short_name="{ item }">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <span v-if="!!item.report_type" v-bind="props">{{
                item.report_type.short_name
              }}</span>
            </template>
            <span v-if="!!item.report_type">{{ item.report_type.name }}</span>
          </v-tooltip>
        </template>
        <template #item.orgs="{ item }">
          <div v-for="org_name in item.orgs" v-bind:key="org_name">
            {{ org_name }}
          </div>
        </template>
        <template #item.actions="{ item }">
          <v-tooltip location="bottom" v-if="item.can_edit">
            <template v-slot:activator="{ props }">
              <v-btn
                icon
                variant="text"
                size="small"
                density="comfortable"
                color="error"
                @click.stop="
                  selectedMDU = item;
                  showDeleteDialog = true;
                "
                v-bind="props"
              >
                <v-icon size="small">fa fa-trash-alt</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.delete") }}</span>
          </v-tooltip>
          <v-tooltip location="bottom" v-if="item.is_processed">
            <template v-slot:activator="{ props }">
              <v-btn
                icon
                size="small"
                density="comfortable"
                variant="text"
                color="secondary"
                @click.stop="
                  selectedMDU = item;
                  dialogType = 'data';
                  showBatchDialog = true;
                "
                v-bind="props"
              >
                <v-icon size="small">fa fa-microscope</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.show_raw_data") }}</span>
          </v-tooltip>
          <v-tooltip location="bottom" v-if="item.is_processed">
            <template v-slot:activator="{ props }">
              <v-btn
                icon
                density="comfortable"
                variant="text"
                size="small"
                color="secondary"
                @click.stop="
                  selectedMDU = item;
                  dialogType = 'chart';
                  showBatchDialog = true;
                "
                v-bind="props"
              >
                <v-icon size="small">fas fa-chart-bar</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.show_chart") }}</span>
          </v-tooltip>
          <v-tooltip location="bottom" v-if="!item.import_batch">
            <template v-slot:activator="{ props }">
              <v-btn
                icon
                variant="text"
                density="comfortable"
                size="small"
                color="secondary"
                v-bind="props"
                :to="{
                  name: 'platform-upload-data-step-preflight',
                  params: {
                    platformId: item.platform.pk,
                    uploadObjectId: item.pk,
                  },
                }"
              >
                <v-icon size="small">fa fa-external-link-alt</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("mdu_page") }}</span>
          </v-tooltip>
        </template>
        <template #item.data_file="{ item }">
          <v-tooltip location="bottom" v-if="item.data_file">
            <template v-slot:activator="{ props }">
              <v-btn
                variant="text"
                icon
                size="small"
                density="comfortable"
                color="secondary"
                v-bind="props"
                :href="item.data_file"
                target="_blank"
              >
                <v-icon size="small">fa fa-download</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("data_file_tt") }}</span>
          </v-tooltip>
        </template>
        <template #item.state="{ item }">
          <ManualUploadState :state="item.state"></ManualUploadState>
        </template>
      </v-data-table-server>
      <v-dialog v-model="showBatchDialog" v-if="showBatchDialog">
        <v-card class="pt-6">
          <v-card-text>
            <v-container v-if="dialogType === 'data'" fluid class="pb-0">
              <v-row class="pb-0">
                <v-col cols="12" class="pb-0">
                  <AccessLogList
                    :mdu-id="selectedMDU.pk"
                    :show-organization="selectedMDUwithMultipleOrg"
                  ></AccessLogList>
                </v-col>
              </v-row>
            </v-container>
            <MDUChart
              v-else-if="dialogType === 'chart' && selectedMDU"
              :mdu-id="selectedMDU.pk"
            ></MDUChart>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              @click="showBatchDialog = false"
              variant="flat"
              elevation="2"
              color="defaultButton"
              class="mr-2 mb-2"
            >
              {{ $t("actions.close") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-dialog
        v-model="showDeleteDialog"
        v-if="showDeleteDialog"
        max-width="720px"
      >
        <v-card>
          <v-card-title>{{ $t("confirm_delete") }}</v-card-title>
          <v-card-text>
            <v-container fluid class="pb-0">
              <v-row>
                <v-col cols="12">
                  {{ $t("delete_warning") }}
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12" class="pb-0">
                  <table v-if="selectedMDU" class="overview">
                    <tr>
                      <th v-text="$t('platform')"></th>
                      <td>{{ selectedMDU.platform.name }}</td>
                    </tr>
                    <tr v-if="selectedMDU.organization">
                      <th v-text="$t('organization')"></th>
                      <td>{{ selectedMDU.organization.name }}</td>
                    </tr>
                    <tr
                      v-else-if="
                        selectedMDU &&
                        selectedMDU.preflight &&
                        selectedMDU.preflight.organizations
                      "
                      v-for="(org_name, idx) in Object.keys(
                        selectedMDU.preflight.organizations,
                      )"
                      v-bind:key="org_name"
                    >
                      <th v-text="$t('organization')" v-if="idx == 0"></th>
                      <th v-else></th>
                      <!-- This is the name of the organization found in data -->
                      <td>{{ org_name }}</td>
                    </tr>
                    <tr v-if="!!selectedMDU.report_type">
                      <th v-text="$t('labels.report_type')"></th>
                      <td>
                        {{ selectedMDU.report_type.short_name }} –
                        {{ selectedMDU.report_type.name }}
                      </td>
                    </tr>
                    <tr>
                      <th v-text="$t('labels.user')"></th>
                      <td>{{ userToString(selectedMDU.user) }}</td>
                    </tr>
                    <tr>
                      <th v-text="$t('title_fields.uploaded')"></th>
                      <td>{{ isoDateTimeFormat(selectedMDU.created) }}</td>
                    </tr>
                  </table>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              @click="showDeleteDialog = false"
              class="mr-2 mb-2"
              color="secondary"
              variant="flat"
              elevation="2"
            >
              {{ $t("actions.cancel") }}
            </v-btn>
            <v-btn
              @click="performDelete()"
              variant="flat"
              elevation="2"
              class="mr-2 mb-2"
              color="error"
            >
              <v-icon size="small" class="mr-1">fa fa-trash-alt</v-icon>
              {{ $t("actions.delete") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card-text>
  </v-card>
</template>

<script>
import debounce from "lodash/debounce";
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import AccessLogList from "./AccessLogList";
import { isoDateTimeFormat, isoDateTimeFormatSpans } from "../libs/dates";
import ManualUploadState from "@/components/ManualUploadState";
import { userToString } from "../libs/user";
import MDUChart from "@/components/MDUChart";
import cancellation from "@/mixins/cancellation";
import stateTracking from "@/mixins/stateTracking";
import TableCustomSort from "@/components/tables/TableCustomSort";

export default {
  name: "ManualUploadListTable",

  mixins: [cancellation, stateTracking],

  components: {
    MDUChart,
    ManualUploadState,
    AccessLogList,
    TableCustomSort,
  },

  data() {
    return {
      mdus: [],
      loading: false,
      showBatchDialog: false,
      showDeleteDialog: false,
      selectedMDU: null,
      search: "",
      filterReportTypes: [],
      reportTypes: [],
      filterPlatforms: [],
      orderByCr: [{ key: "created", order: "desc" }],
      platforms: [],
      counts: null,
      mduCount: 0,
      page: 1,
      pageSize: 10,
      changingOrganization: false,
      watchedAttrs: [
        {
          name: "search",
          type: String,
        },
        {
          name: "filterPlatforms",
          type: Array,
        },
        {
          name: "filterReportTypes",
          type: Array,
        },
        {
          name: "orderByCr",
          type: Array,
        },
        {
          alwaysTrack: true,
        },
      ],
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
      organizations: "organizations",
    }),
    ...mapGetters({
      organizationSelected: "organizationSelected",
    }),
    selectedMDUwithMultipleOrg() {
      return !!this.selectedMDU?.preflight?.organizations;
    },
    headers() {
      const out = [
        {
          title: this.$t("title_fields.uploaded"),
          value: "created",
          key: "created",
          order: "reverse",
        },
        {
          title: this.$t("platform"),
          value: "platform.name",
          key: "platform.name",
        },
        {
          title: this.$t("labels.report_type"),
          value: "report_type.short_name",
          key: "report_type.short_name",
        },
        {
          title: this.$t("labels.user"),
          value: "user.last_name",
          key: "user.last_name",
        },
        {
          title: this.$t("state"),
          value: "state",
          key: "state",
        },
        {
          title: this.$t("data_file"),
          value: "data_file",
          sortable: false,
        },
        {
          title: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
      if (!this.organizationSelected) {
        out.splice(1, 0, {
          title: this.$t("organization"),
          value: "organization.name",
        });
      }
      return out;
    },
    organizationMap() {
      return Object.values(this.organizations).reduce(
        (acc, o) => ({ ...acc, [o.pk]: o }),
        {},
      );
    },
    mdusProcessed() {
      let res = [];
      for (const record of this.mdus) {
        // apply filters
        if (
          this.filterReportTypes.length > 0 &&
          !this.filterReportTypes.includes(record.report_type?.pk)
        ) {
          continue;
        }
        if (
          this.filterPlatforms.length > 0 &&
          !this.filterPlatforms.includes(record.platform.pk)
        ) {
          continue;
        }

        let updated = { ...record };
        if (record.organization) {
          updated.orgs = [record.organization.name];
        } else {
          if (record.preflight && record.preflight.organizations) {
            updated.orgs = Object.entries(record.preflight.organizations).map(
              ([raw_name, data]) => {
                if ("pk" in data) {
                  if (data["pk"] in this.organizationMap) {
                    return this.organizationMap[data["pk"]].name;
                  }
                }
                return raw_name;
              },
            );
          } else {
            updated.orgs = [];
          }
        }
        res.push(updated);
      }
      return res;
    },
    urlFilters() {
      let params = {};
      if (this.filterReportTypes.length > 0) {
        params.report_type_ids = `${this.filterReportTypes}`;
      }
      if (this.filterPlatforms.length > 0) {
        params.platform_ids = `${this.filterPlatforms}`;
      }
      if (this.orderByCr.length > 0) {
        let orderBy = this.orderByCr[0]
          ? this.orderByCr[0].key.replace(".", "__")
          : "created";
        params.order_by = `${orderBy}`;
        params.desc = this.orderByCr[0]
          ? `${this.orderByCr[0].order === "desc" ? true : false}`
          : null;
      }
      if (this.searchDebounced) {
        params.search = `${this.searchDebounced}`;
      }
      if (this.pageSize) {
        params.page_size = `${this.pageSize}`;
      }

      return params;
    },
    url() {
      if (this.selectedOrganizationId) {
        let url = `/api/organization/${this.selectedOrganizationId}/manual-data-upload/`;
        let params = this.urlFilters;
        if (this.page) {
          params.page = `${this.page}`;
        }
        return this.$router.resolve({ path: url, query: params }).href;
      }
      return null;
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    platformsBaseUrl() {
      return `/api/organization/${this.selectedOrganizationId}/all-platform/`;
    },
    reportTypesBaseUrl() {
      return `/api/organization/${this.selectedOrganizationId}/report-types/`;
    },
    mduStatsBaseUrl() {
      return `/api/organization/${this.selectedOrganizationId}/manual-data-upload/stats/`;
    },
    filteredPlatforms() {
      let res = [];
      if (this.counts) {
        const platformIds = this.counts.platforms.map((e) => e.platform_id);
        res = this.platforms.filter((e) => platformIds.includes(e.pk));
      } else {
        res = [...this.platforms];
      }
      res.sort((a, b) => a.name.localeCompare(b.name));
      return res;
    },
    filteredReportTypes() {
      let res = [];
      if (this.counts) {
        const reportTypeIds = this.counts.report_types.map(
          (e) => e.report_type_id,
        );
        res = this.reportTypes.filter((e) => reportTypeIds.includes(e.pk));
      } else {
        res = [...this.reportTypes];
      }
      res.sort((a, b) => a.name.localeCompare(b.name));
      return res;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    isoDateTimeFormat: isoDateTimeFormat,
    isoDateTimeFormatSpans: isoDateTimeFormatSpans,
    userToString: userToString,
    async fetchMDUs() {
      if (this.url) {
        this.loading = true;
        const reply = await this.http({
          url: this.url,
          group: "mdu-list",
        });
        if (!reply.error) {
          this.mdus = reply.response.data.results;
          this.mduCount = reply.response.data.count;
        }
        if (reply.error !== "canceled") {
          // if the request was cancelled, it means another request was made
          // so we do not want to swich loading off
          this.loading = false;
        }
      }
    },
    performDelete() {
      try {
        axios.delete(`/api/manual-data-upload/${this.selectedMDU.pk}/`);
        this.showSnackbar({
          content: this.$t("delete_success"),
          color: "success",
        });
        this.showDeleteDialog = false;
        this.mdus = this.mdus.filter((item) => item.pk !== this.selectedMDU.pk);
        this.selectedMDU = null;
      } catch (error) {
        this.showSnackbar({
          content: "Error deleting manual data upload: " + error,
          color: "error",
        });
      }
    },
    // Merge current filters with available options, keeping only valid ones
    mergeFilters(currentFilter, filtered) {
      if (currentFilter.length > 0) {
        const availableFilters = currentFilter.filter((id) =>
          filtered.map((p) => p.pk).includes(id),
        );
        if (availableFilters.length !== currentFilter.length) {
          return availableFilters;
        }
      }
      return currentFilter;
    },
    async fetchStats() {
      const reply = await this.http({
        url: this.mduStatsBaseUrl,
        group: "mdu-platforms",
      });
      if (!reply.error) {
        this.counts = reply.response.data.counts;
      }
    },
    async fetchPlatforms() {
      const reply = await this.http({
        url: this.platformsBaseUrl,
        group: "mdu-platforms",
      });
      if (!reply.error) {
        this.platforms = reply.response.data;
      }
    },
    async fetchReportTypes() {
      const reply = await this.http({
        url: this.reportTypesBaseUrl,
        group: "mdu-report-types",
      });
      if (!reply.error) {
        this.reportTypes = reply.response.data;
      }
    },
    async refetchFilters() {
      await this.fetchStats();
      this.fetchPlatforms();
      this.fetchReportTypes();
    },
  },

  watch: {
    urlFilters() {
      this.page = 1; // reset page when filter changes
    },
    url() {
      if (!this.changingOrganization) {
        this.fetchMDUs();
      }
    },
    selectedOrganizationId() {
      this.changingOrganization = true;
      this.page = 1;
      this.$nextTick(() => {
        this.refetchFilters();
        this.fetchMDUs();
        this.changingOrganization = false;
      });
    },
    filteredPlatforms() {
      this.filterPlatforms = this.mergeFilters(
        this.filterPlatforms,
        this.filteredPlatforms,
      );
    },
    filteredReportTypes() {
      this.filterReportTypes = this.mergeFilters(
        this.filterReportTypes,
        this.filteredReportTypes,
      );
    },
  },

  mounted() {
    this.fetchMDUs();
    this.refetchFilters();
  },
};
</script>
