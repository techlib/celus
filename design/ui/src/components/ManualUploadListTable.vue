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
            <v-select
              v-model="filterPlatforms"
              :label="$t('title_fields.platforms')"
              :items="platforms"
              item-value="pk"
              item-text="name"
              multiple
              clearable
              clear-icon="fas fa-times"
            ></v-select>
          </v-col>
          <v-col md="4" cols="12">
            <v-select
              v-model="filterReportTypes"
              :label="$t('title_fields.report_types')"
              :items="reportTypes"
              item-value="pk"
              item-text="name"
              multiple
              clearable
              clear-icon="fas fa-times"
            ></v-select>
          </v-col>
          <v-col md="4" cols="12">
            <v-text-field
              v-model="search"
              append-icon="fa-search"
              :label="$t('labels.search')"
              single-line
              hide-details
            >
            </v-text-field>
          </v-col>
        </v-row>
      </v-container>
      <v-data-table
        :items="mdusProcessed"
        :headers="headers"
        :no-data-text="$t('no_data')"
        :loading="loading"
        :footer-props="{ itemsPerPageOptions: [10, 25, 50] }"
        sort-by="created"
        sort-desc
        :search="search"
      >
        <template #item.user.last_name="{ item }">
          {{ userToString(item.user) }}
        </template>

        <template #item.created="{ item }">
          <span v-html="isoDateTimeFormatSpans(item.created)"></span>
        </template>

        <template #item.report_type.short_name="{ item }">
          <v-tooltip bottom v-if="item.can_edit">
            <template v-slot:activator="{ on }">
              <span
                v-if="!!item.report_type"
                v-on="on"
                v-text="item.report_type.short_name"
              ></span>
            </template>
            <span
              v-if="!!item.report_type"
              v-text="item.report_type.name"
            ></span>
          </v-tooltip>
        </template>

        <template #item.orgs="{ item }">
          <div v-for="org_name in item.orgs" v-bind:key="org_name">
            {{ org_name }}
          </div>
        </template>

        <template #item.actions="{ item }">
          <v-tooltip bottom v-if="item.can_edit">
            <template v-slot:activator="{ on }">
              <v-btn
                icon
                small
                color="error"
                @click.stop="
                  selectedMDU = item;
                  showDeleteDialog = true;
                "
                v-on="on"
              >
                <v-icon small>fa fa-trash-alt</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.delete") }}</span>
          </v-tooltip>
          <v-tooltip bottom v-if="item.is_processed">
            <template v-slot:activator="{ on }">
              <v-btn
                icon
                small
                color="secondary"
                @click.stop="
                  selectedMDU = item;
                  dialogType = 'data';
                  showBatchDialog = true;
                "
                v-on="on"
              >
                <v-icon small>fa-microscope</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.show_raw_data") }}</span>
          </v-tooltip>
          <v-tooltip bottom v-if="item.is_processed">
            <template v-slot:activator="{ on }">
              <v-btn
                icon
                small
                color="secondary"
                @click.stop="
                  selectedMDU = item;
                  dialogType = 'chart';
                  showBatchDialog = true;
                "
                v-on="on"
              >
                <v-icon small>fa-chart-bar</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("actions.show_chart") }}</span>
          </v-tooltip>
          <v-tooltip bottom v-if="!item.import_batch">
            <template v-slot:activator="{ on }">
              <v-btn
                icon
                small
                color="secondary"
                v-on="on"
                :to="{
                  name: 'platform-upload-data-step-preflight',
                  params: {
                    platformId: item.platform.pk,
                    uploadObjectId: item.pk,
                  },
                }"
              >
                <v-icon small>fa-external-link-alt</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("mdu_page") }}</span>
          </v-tooltip>
        </template>

        <template #item.data_file="{ item }">
          <v-tooltip bottom v-if="item.data_file">
            <template v-slot:activator="{ on }">
              <v-btn
                icon
                small
                color="secondary"
                v-on="on"
                :href="item.data_file"
                target="_blank"
              >
                <v-icon small>fa-download</v-icon>
              </v-btn>
            </template>
            <span>{{ $t("data_file_tt") }}</span>
          </v-tooltip>
        </template>

        <template #item.state="{ item }">
          <ManualUploadState :state="item.state" />
        </template>
      </v-data-table>

      <v-dialog v-model="showBatchDialog">
        <v-card>
          <v-card-text>
            <v-container v-if="dialogType === 'data'" fluid class="pb-0">
              <v-row class="pb-0">
                <v-col cols="12" class="pb-0">
                  <AccessLogList
                    :mdu-id="selectedMDU.pk"
                    :show-organization="selectedMDUwithMultipleOrg"
                  />
                </v-col>
              </v-row>
            </v-container>
            <MDUChart
              v-else-if="dialogType === 'chart' && selectedMDU"
              :mdu-id="selectedMDU.pk"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="showBatchDialog = false" class="mr-2 mb-2">
              {{ $t("actions.close") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="showDeleteDialog" max-width="720px">
        <v-card>
          <v-card-title v-text="$t('confirm_delete')"></v-card-title>
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
                        selectedMDU.preflight.organizations
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
                        {{ selectedMDU.report_type.short_name }} &ndash;
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
            >
              {{ $t("actions.cancel") }}
            </v-btn>
            <v-btn @click="performDelete()" class="mr-2 mb-2" color="error">
              <v-icon small class="mr-1">fa fa-trash-alt</v-icon>
              {{ $t("actions.delete") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card-text>
  </v-card>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import AccessLogList from "./AccessLogList";
import { isoDateTimeFormat, isoDateTimeFormatSpans } from "../libs/dates";
import ManualUploadState from "@/components/ManualUploadState";
import { userToString } from "../libs/user";
import MDUChart from "@/components/MDUChart";
import cancellation from "@/mixins/cancellation";

export default {
  name: "ManualUploadListTable",

  mixins: [cancellation],

  components: {
    MDUChart,
    ManualUploadState,
    AccessLogList,
  },

  data() {
    return {
      mdus: [],
      loading: false,
      showBatchDialog: false,
      showDeleteDialog: false,
      selectedMDU: null,
      dialogType: "chart",
      search: "",
      filterReportTypes: [],
      filterPlatforms: [],
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
          text: this.$t("title_fields.uploaded"),
          value: "created",
        },
        {
          text: this.$t("platform"),
          value: "platform.name",
        },
        {
          text: this.$t("labels.report_type"),
          value: "report_type.short_name",
        },
        {
          text: this.$t("labels.user"),
          value: "user.last_name",
        },
        {
          text: this.$t("state"),
          value: "state",
        },
        {
          text: this.$t("data_file"),
          value: "data_file",
          sortable: false,
        },
        {
          text: this.$t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
      if (!this.organizationSelected) {
        out.splice(1, 0, {
          text: this.$t("organization"),
          value: "orgs",
        });
      }
      return out;
    },
    organizationMap() {
      return Object.values(this.organizations).reduce(
        (acc, o) => ({ ...acc, [o.pk]: o }),
        {}
      );
    },
    mdusProcessed() {
      let res = [];
      for (const record of this.mdus) {
        // apply filters
        if (
          this.filterReportTypes.length > 0 &&
          !this.filterReportTypes.includes(record.report_type.pk)
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
              }
            );
          } else {
            updated.orgs = [];
          }
        }
        res.push(updated);
      }
      return res;
    },
    reportTypes() {
      // derived from data
      // extract unique report types
      let res = Object.values(
        this.mdus
          .filter((mdu) => mdu.report_type)
          .map((mdu) => mdu.report_type)
          .reduce((acc, rt) => ({ ...acc, [rt.pk]: rt }), {})
      );
      // sort report types
      res.sort((a, b) => a.name.localeCompare(b.name));
      return res;
    },
    platforms() {
      // derived from data
      // extract unique report types
      let res = Object.values(
        this.mdus
          .map((mdu) => mdu.platform)
          .reduce((acc, p) => ({ ...acc, [p.pk]: p }), {})
      );
      // sort report types
      res.sort((a, b) => a.name.localeCompare(b.name));
      return res;
    },
    url() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/manual-data-upload/`;
      }
      return null;
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
        const result = await this.http({
          url: this.url,
          group: "mdu-list",
        });
        if (!result.error) {
          this.mdus = result.response.data;
        }
        if (result.error !== "canceled") {
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
  },

  watch: {
    url() {
      this.fetchMDUs();
    },
  },

  mounted() {
    this.fetchMDUs();
  },
};
</script>
