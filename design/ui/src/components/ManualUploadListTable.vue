<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  state: State
  delete_warning:
    You are about to delete this manually uploaded data from the database.
    Please confirm this action.
  delete_success: Successfully deleted selected manually uploaded data
  mdu_page: To processing page
  no_data: There are no manually uploaded data yet

cs:
  state: Stav
  delete_warning: Prosím potvrďte, že chcete smazat z databáze tato ručně nahraná data.
  delete_success: Vybraná ručně nahraná data byla úspěšně smazána
  mdu_page: Na stránku zpracování
  no_data: Zatím nebyla ručně nahrána žádná data
</i18n>

<template>
  <div>
    <v-data-table
      :items="mdus"
      :headers="headers"
      :no-data-text="$t('no_data')"
      :loading="loading"
      sort-by="created"
      sort-desc
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
            <span v-on="on" v-text="item.report_type.short_name"></span>
          </template>
          <span v-text="item.report_type.name"></span>
        </v-tooltip>
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
                name: 'platform-upload-data-step2',
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
                <AccessLogList :mdu-id="selectedMDU.pk" />
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
                  <tr>
                    <th v-text="$t('organization')"></th>
                    <td>{{ selectedMDU.organization.name }}</td>
                  </tr>
                  <tr>
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
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import AccessLogList from "./AccessLogList";
import { isoDateTimeFormat, isoDateTimeFormatSpans } from "../libs/dates";
import ManualUploadState from "@/components/ManualUploadState";
import { userToString } from "../libs/user";
import MDUChart from "@/components/MDUChart";

export default {
  name: "ManualUploadListTable",

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
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      organizationSelected: "organizationSelected",
    }),
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
          text: this.$t("title_fields.actions"),
          value: "actions",
        },
      ];
      if (!this.organizationSelected) {
        out.splice(1, 0, {
          text: this.$t("organization"),
          value: "organization.name",
        });
      }
      return out;
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
        try {
          const response = await axios.get(this.url);
          this.mdus = response.data;
        } catch (error) {
          this.showSnackbar({
            content: "Error loading manual upload data",
            color: "error",
          });
        } finally {
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
