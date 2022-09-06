<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml" src="@/locales/sushi.yaml"></i18n>
<i18n lang="yaml">
en:
  add_new: Add new SUSHI
  export: Export
  export_selected: Selected
  export_all: All
  export_tooltip: Export credentials into CSV
  is_locked: These credentials are locked.
  is_unlocked: These credentials are not locked, you may edit them.
  cannot_edit: You cannot edit them.
  can_edit: Because of your privileges, you can still edit them.
  can_lock: You may lock/unlock these credentials - click to do so.
  test_checked: Harvest
  test_checked_tooltip: Opens a dialog for one-off harvesting of data for all selected SUSHI credentials.
  test_dialog: Manual SUSHI harvesting
  is_broken: |
    These credentials have been marked as broken because of harvesting failures.
    Automatic harvesting was postponed until the credentials are manually fixed.
  no_credentials_selected: No credentials selected
  select_at_least_one_credentials: Please select at least one set of SUSHI credentials using the checkboxes in the credentials list.
  unverified_tooltip: No data has been obtained yet using the current version of these credentials. Please verify the credentials by manually harvesting some data.
cs:
  add_new: Přidat nové SUSHI
  export: Exportuj
  export_selected: Vybrané
  export_all: Všechny
  export_tooltip: Exportovat přístupové údaje do CSV
  is_locked: Tyto přístupové údaje jsou uzamčené.
  is_unlocked: Tyto přístupové údaje nejsou uzamčené, můžete je editovat
  cannot_edit: Nemůžete je editovat.
  can_edit: Vaše oprávnění Vám umožňují je přesto editovat.
  can_lock: Kliknutím můžete tyto údaje uzamknout/odemknout.
  test_checked: Stáhni
  test_checked_tooltip: Otevře dialog pro jednorázové stažení dat pro všechny vybrané přístupové údaje SUSHI.
  test_dialog: Manuální stahování SUSHI
  is_broken: |
    Tyto přihlašovací údaje byly označeny jako nefunkční, kvůli neúspěchům při stahování. Automatické stahování
    bylo pozastaveno do doby než budou údaje ručně opraveny.
  no_credentials_selected: Nejsou vybrány žádné přihlašovací údaje
  select_at_least_one_credentials: Vyberte prosím alespoň jedny přihlašovací údaje pomocí zaškrtávacích polí v seznamu přihlašovacích údajů.
  unverified_tooltip: Žádná data zatím nebyla stažena se současnou verzí těchto přístupových údajů. Ověřte prosím platnost přihlašovacích údajů manuálním stažením dat.
</i18n>

<template>
  <v-container fluid>
    <v-card>
      <v-card-title>
        <v-container fluid>
          <v-row>
            <v-col cols="auto" align-self="center">
              <v-btn @click="activateCreateDialog()" color="warning">
                <v-icon small class="mr-2">fa-plus</v-icon>
                {{ $t("add_new") }}
              </v-btn>
            </v-col>
            <v-col cols="auto" align-self="center">
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-btn @click="testChecked()" color="success" v-on="on">
                    <v-icon small class="mr-2">fa fa-download</v-icon>
                    {{ $t("test_checked") }}
                    <v-badge color="white" inline>
                      <template #badge>
                        <span class="success--text">{{
                          checkedCredentials.length
                        }}</span>
                      </template>
                    </v-badge>
                  </v-btn>
                </template>
                {{ $t("test_checked_tooltip") }}
              </v-tooltip>
            </v-col>
            <v-col cols="auto" align-self="center">
              <v-tooltip right>
                <template #activator="tooltip">
                  <v-menu offset-y>
                    <template #activator="menu">
                      <v-btn
                        v-on="{ ...menu.on, ...tooltip.on }"
                        color="primary"
                      >
                        <v-icon small class="mr-2">fas fa-file-export</v-icon>
                        {{ $t("export") }}
                      </v-btn>
                    </template>
                    <v-list>
                      <form
                        action="/api/sushi-credentials/export-credentials/"
                        method="post"
                      >
                        <input
                          type="hidden"
                          name="csrfmiddlewaretoken"
                          :value="getCSRFToken"
                          style="display: none"
                        />
                        <div
                          v-for="checkedCredential in checkedCredentials"
                          :key="checkedCredential.pk"
                          style="display: none"
                        >
                          <input
                            type="hidden"
                            :id="checkedCredential.pk"
                            name="pk"
                            :value="checkedCredential.pk"
                          />
                        </div>
                        <input
                          :type="
                            checkedCredentials.length > 0 ? 'submit' : undefined
                          "
                          id="submitform"
                          style="display: none"
                        />
                        <label for="submitform">
                          <v-list-item @click="showSelectCredentials">
                            <v-list-item-title>
                              {{ $t("export_selected") }}
                              <v-badge inline color="secondary" class="mt-0">
                                <template #badge>
                                  <span class="white--text">{{
                                    checkedCredentials.length
                                  }}</span>
                                </template>
                              </v-badge>
                            </v-list-item-title>
                          </v-list-item>
                        </label>
                      </form>
                      <form :action="exportUrl" method="post">
                        <input
                          type="hidden"
                          name="csrfmiddlewaretoken"
                          :value="getCSRFToken"
                          style="display: none"
                        />
                        <input
                          type="submit"
                          id="exportAll"
                          style="display: none"
                        />
                        <label for="exportAll">
                          <v-list-item @click="downloadAll">
                            <v-list-item-title>
                              {{ $t("export_all") }}
                            </v-list-item-title>
                          </v-list-item>
                        </label>
                      </form>
                    </v-list>
                  </v-menu>
                </template>
                {{ $t("export_tooltip") }}
              </v-tooltip>
            </v-col>
            <v-spacer></v-spacer>

            <v-col cols="auto">
              <v-switch
                v-model="problematicOnly"
                :label="$t('labels.problematic_only')"
              ></v-switch>
            </v-col>
            <v-col cols="3" :md="2" :xl="1">
              <v-select
                :items="[
                  { text: '4 + 5', value: null },
                  { text: '4', value: 4 },
                  { text: '5', value: 5 },
                ]"
                v-model="counterVersion"
                :label="$t('labels.counter_version')"
              ></v-select>
            </v-col>
            <v-col cols="auto" class="ml-auto">
              <v-text-field
                v-model="searchDebounced"
                append-icon="fa-search"
                :label="$t('labels.search')"
                single-line
                hide-details
                clearable
                clear-icon="fa-times"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-container>
      </v-card-title>

      <v-data-table
        v-model="checkedRows"
        :items="visibleSushiCredentials"
        :headers="headers"
        :items-per-page.sync="itemsPerPage"
        :sort-by="orderBy"
        multi-sort
        :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
        :loading="loading"
        show-select
        item-key="pk"
        ref="credentialsTable"
      >
        <template v-slot:item.counter_reports="{ item }">
          <v-chip
            v-for="(report, index) in item.counter_reports_long"
            :key="index"
            class="mr-1 px-2"
            :color="report.broken ? '#888888' : 'teal'"
            outlined
            label
          >
            <SushiReportIndicator :report="report" />
          </v-chip>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn
            v-if="!item.locked_for_me"
            text
            small
            color="secondary"
            @click.stop="
              selectedCredentials = item;
              showEditDialog = true;
            "
          >
            <v-icon left x-small>fa-edit</v-icon>
            {{ $t("actions.edit") }}
          </v-btn>
          <v-btn
            text
            small
            color="secondary"
            @click.stop="
              selectedCredentials = item;
              showDetailsDialog = true;
            "
          >
            <v-icon left x-small>fa-list</v-icon>
            {{ $t("actions.show_attempts") }}
          </v-btn>
          <v-tooltip left>
            <template v-slot:activator="{ on }">
              <v-btn
                v-on="on"
                text
                small
                color="secondary"
                @click.stop="
                  selectedCredentials = item;
                  showDataDialog = true;
                "
              >
                <v-icon left x-small>far fa-calendar-alt</v-icon>
                {{ $t("actions.show_overview") }}
              </v-btn>
            </template>
            {{ $t("actions.show_overview_details") }}
          </v-tooltip>
        </template>
        <template v-slot:item.enabled="{ item }">
          <CheckMark
            :value="item.enabled"
            true-color="error"
            false-color="error"
            v-if="item.broken"
          />
          <CheckMark
            :value="item.enabled"
            true-color="warning"
            false-color="warning"
            v-else-if="!item.verified"
          />
          <CheckMark :value="item.enabled" v-else />
          <v-tooltip bottom v-if="item.broken" max-width="400">
            <template v-slot:activator="{ on }">
              <v-btn text icon v-on="on"
                ><v-icon small color="error">fa-exclamation-triangle</v-icon>
              </v-btn>
            </template>
            {{ $t("is_broken") }}
          </v-tooltip>
          <v-tooltip bottom v-else-if="!item.verified" max-width="400">
            <template v-slot:activator="{ on }">
              <v-btn text icon v-on="on"
                ><v-icon small color="warning">fa-exclamation-triangle</v-icon>
              </v-btn>
            </template>
            {{ $t("unverified_tooltip") }}
          </v-tooltip>
        </template>
        <template v-slot:item.outside_consortium="{ item }">
          <CheckMark :value="item.outside_consortium" />
        </template>
        <template v-slot:item.locked="{ item }">
          <!-- locked for me -->
          <v-tooltip bottom v-if="item.locked && item.locked_for_me">
            <template v-slot:activator="{ on }">
              <v-icon small v-on="on" color="red">fa-fw fa-lock</v-icon>
            </template>
            {{ $t("is_locked") }} {{ $t("cannot_edit") }}
          </v-tooltip>
          <!-- locked, but I can edit -->
          <v-tooltip bottom v-else-if="item.locked">
            <template v-slot:activator="{ on }">
              <v-icon small v-on="on" color="red">fa-fw fa-lock</v-icon>
            </template>
            {{ $t("is_locked") }} {{ $t("can_edit") }}
          </v-tooltip>
          <!-- not locked at all -->
          <v-tooltip bottom v-else>
            <template v-slot:activator="{ on }">
              <v-icon small v-on="on" color="green">fa-fw fa-lock-open</v-icon>
            </template>
            {{ $t("is_unlocked") }}
          </v-tooltip>

          <v-tooltip bottom v-if="item.can_lock">
            <template v-slot:activator="{ on }">
              <v-btn text icon @click="toggleLock(item)" v-on="on"
                ><v-icon small>fa-key</v-icon></v-btn
              >
            </template>
            {{ $t("can_lock") }}
          </v-tooltip>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="showEditDialog" :max-width="dialogMaxWidth">
      <SushiCredentialsEditDialog
        :credentials-object="selectedCredentials"
        v-model="showEditDialog"
        @update-credentials="updateCredentials"
        @deleted="deleteCredentials"
        @set-dirty="reloadSelectedCredentials"
        :existing-credentials="sushiCredentialsList"
        key="edit"
      ></SushiCredentialsEditDialog>
    </v-dialog>

    <v-dialog v-model="showCreateDialog" :max-width="dialogMaxWidth">
      <SushiCredentialsEditDialog
        v-model="showCreateDialog"
        @update-credentials="updateCredentials"
        @set-dirty="reloadSelectedCredentials"
        :existing-credentials="sushiCredentialsList"
        key="create"
        :fixed-platform="platformId"
      ></SushiCredentialsEditDialog>
    </v-dialog>

    <v-dialog v-model="showDetailsDialog">
      <SushiAttemptListWidget
        v-if="selectedCredentials"
        :credentials="selectedCredentials"
        @close="closeDetailsDialog"
      >
      </SushiAttemptListWidget>
    </v-dialog>

    <v-dialog
      v-model="showTestDialog"
      max-width="1320px"
      content-class="top-dialog"
    >
      <v-card>
        <v-card-title>{{ $t("test_dialog") }}</v-card-title>
        <v-card-text class="pb-0">
          <HarvestSelectedWidget
            v-if="showTestDialog"
            :credentials="checkedCredentials"
            ref="testWidget"
            :retry-interval="5000"
            :show-platform="true"
            :show-organization="true"
          >
          </HarvestSelectedWidget>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="secondary"
            @click="stopTestDialog()"
            class="mb-5 mr-5"
            >{{ $t("close") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showDataDialog" :max-width="dialogMaxWidth">
      <SushiCredentialsDataDialog
        v-if="showDataDialog"
        :credentials="selectedCredentials"
        @close="closeDataDialog"
      ></SushiCredentialsDataDialog>
    </v-dialog>
  </v-container>
</template>

<script>
import axios from "axios";
import Cookies from "js-cookie";
import { mapActions, mapGetters } from "vuex";
import debounce from "lodash/debounce";
import SushiCredentialsEditDialog from "@/components/sushi/SushiCredentialsEditDialog";
import SushiAttemptListWidget from "@/components/sushi/SushiAttemptListWidget";
import CheckMark from "@/components/util/CheckMark";
import SushiReportIndicator from "@/components/sushi/SushiReportIndicator";
import SushiCredentialsDataDialog from "@/components/sushi/SushiCredentialsDataDialog";
import HarvestSelectedWidget from "@/components/sushi/HarvestSelectedWidget";

export default {
  name: "SushiCredentialsManagementWidget",

  components: {
    HarvestSelectedWidget,
    SushiReportIndicator,
    SushiCredentialsEditDialog,
    SushiAttemptListWidget,
    SushiCredentialsDataDialog,
    CheckMark,
  },

  props: {
    dialogMaxWidth: {
      required: false,
      default: "1200px",
    },
    organizationId: {
      default: -1,
      type: Number,
      required: false,
    },
    platformId: {
      default: null,
      type: Number,
      required: false,
    },
    showProblematicOnly: {
      default: false,
      type: Boolean,
    },
  },

  data() {
    return {
      sushiCredentialsList: [],
      search: "",
      itemsPerPage: 25,
      selectedCredentials: null,
      showEditDialog: false,
      showDetailsDialog: false,
      showCreateDialog: false,
      showDataDialog: false,
      orderBy: ["organization.name", "platform.name", "counter_version"],
      loading: false,
      counterVersion: null,
      checkedRows: [],
      showTestDialog: false,
      problematicOnly: this.showProblematicOnly,
      exportAllCredentialsUrl:
        "/api/sushi-credentials/export-all-credentials/?export_all=true",
    };
  },
  computed: {
    ...mapGetters({
      consortialInstall: "consortialInstall",
    }),
    getCSRFToken() {
      let csrftoken = Cookies.get("csrftoken");
      return csrftoken;
    },
    headers() {
      const large = this.$vuetify.breakpoint.lgAndUp;
      let allHeaders = [
        {
          text: this.$i18n.t("title"),
          value: "title",
          class: "wrap",
        },
        {
          text: this.$i18n.t("organization"),
          value: "organization.name",
          class: "wrap",
        },
        {
          text: this.$i18n.t("platform"),
          value: "platform.name",
        },
        {
          text: this.$i18n.t("title_fields.counter_version"),
          value: "counter_version",
          align: "end",
        },
        {
          text: this.$i18n.t("title_fields.active_reports"),
          value: "counter_reports",
          sortable: false,
        },
        {
          text: this.$i18n.t("title_fields.outside_consortium"),
          value: "outside_consortium",
          show: this.consortialInstall && large,
        },
        {
          text: this.$i18n.t("sushi.enabled"),
          value: "enabled",
        },
        {
          text: this.$i18n.t("title_fields.lock"),
          value: "locked",
          show: this.consortialInstall && large,
        },
        {
          text: this.$i18n.t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
      return allHeaders.filter(
        (row) => !row.hasOwnProperty("show") || row.show
      );
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    dataUrl() {
      let base = `/api/sushi-credentials/?organization=${this.organizationId}`;
      if (this.platformId) {
        base += `&platform=${this.platformId}`;
      }
      return base;
    },
    visibleSushiCredentials() {
      return this.sushiCredentialsList
        .filter((item) =>
          this.problematicOnly
            ? !item.verified || item.broken || item.has_broken_reports
            : true
        )
        .filter(
          (item) =>
            this.counterVersion === null ||
            this.counterVersion === item.counter_version
        )
        .filter(this.createSearchFilter());
    },
    checkedCredentials() {
      let visibleIds = new Set(
        this.visibleSushiCredentials.map((item) => item.pk)
      );
      return this.checkedRows.filter((item) => visibleIds.has(item.pk));
    },
    exportUrl() {
      let base = `/api/sushi-credentials/export-credentials/?organization=${this.organizationId}`;
      if (this.platformId) {
        base += `&platform=${this.platformId}`;
      }
      return base;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
      loadSushiCredentialsCount: "loadSushiCredentialsCount",
    }),
    showSelectCredentials() {
      if (this.checkedCredentials.length === 0) {
        this.$confirm(this.$t("select_at_least_one_credentials"), {
          title: this.$t("no_credentials_selected"),
          buttonTrueText: this.$t("close"),
          buttonFalseText: null,
        });
      }
    },
    downloadAll() {
      return true;
    },
    async loadSushiCredentialsList() {
      this.loading = true;
      try {
        let response = await axios.get(this.dataUrl);
        this.sushiCredentialsList = response.data;
        this.sushiCredentialsList.forEach((item) =>
          this.preprocessCredentials(item)
        );
      } catch (error) {
        this.showSnackbar({
          content: "Error loading credentials list: " + error,
        });
      } finally {
        this.loading = false;
      }
    },
    async reloadSelectedCredentials() {
      if (this.selectedCredentials) {
        try {
          let response = await axios.get(
            `/api/sushi-credentials/${this.selectedCredentials.pk}/`
          );
          this.updateCredentials(response.data);
        } catch (error) {
          this.showSnackbar({
            content: "Could not reload credentials: " + error,
            color: "error",
          });
        }
      }
    },
    updateCredentials(credentials) {
      this.preprocessCredentials(credentials);
      // the new credentials as returned by the edit dialog
      // we put them at the right place in the list of credentials
      let found = false;
      for (let i = 0; i < this.sushiCredentialsList.length; i++) {
        if (this.sushiCredentialsList[i].pk === credentials.pk) {
          this.$set(this.sushiCredentialsList, i, credentials);
          found = true;
          break;
        }
      }
      // checkedRows contains a copy of the credentials, so we need to update it as well
      for (let i = 0; i < this.checkedRows.length; i++) {
        if (this.checkedRows[i].pk === credentials.pk) {
          this.$set(this.checkedRows, i, credentials);
          break;
        }
      }
      if (!found) {
        // we did not find the corresponding record - we add it at the end
        this.sushiCredentialsList.push(credentials);
      }
      // update the model used by the edit dialog
      if (this.selectedCredentials) {
        this.selectedCredentials = credentials;
      }
    },
    deleteCredentials({ id }) {
      this.sushiCredentialsList = this.sushiCredentialsList.filter(
        (item) => item.pk !== id
      );
    },
    preprocessCredentials(item) {
      item["has_broken_reports"] = !!item.counter_reports_long.filter(
        (report) => report.broken
      ).length;
      //tem["isSelectable"] = !item.broken;
      if (item.broken) {
        // we need to make sure a broken item is not checked
        this.checkedRows = this.checkedRows.filter((row) => row.pk !== item.pk);
      }
      if (!item.platform.name) {
        // use platform short_name instead of name if name is empty
        item.platform.name = item.platform.short_name;
      }
    },
    async toggleLock(credentials) {
      let newLockLevel = 400;
      if (credentials.locked) {
        newLockLevel = 300;
      }
      try {
        let response = await axios.post(
          `/api/sushi-credentials/${credentials.pk}/lock/`,
          { lock_level: newLockLevel }
        );
        credentials.lock_level = response.data.lock_level;
        credentials.locked = response.data.locked;
      } catch (error) {
        this.showSnackbar({
          content: "Error (un)locking credentials: " + error,
          color: "error",
        });
      }
    },
    closeDetailsDialog() {
      this.selectedCredentials = null;
      this.showDetailsDialog = false;
    },
    closeDataDialog() {
      this.selectedCredentials = null;
      this.showDataDialog = false;
    },
    activateCreateDialog() {
      this.showCreateDialog = true;
    },
    testChecked() {
      if (this.checkedCredentials.length > 0) {
        this.showTestDialog = true;
      } else {
        this.$confirm(this.$t("select_at_least_one_credentials"), {
          title: this.$t("no_credentials_selected"),
          buttonTrueText: this.$t("close"),
          buttonFalseText: null,
        });
      }
    },
    stopTestDialog() {
      if (this.$refs.testWidget) {
        this.$refs.testWidget.clean();
      }
      this.showTestDialog = false;
      this.loadSushiCredentialsList();
      this.loadSushiCredentialsCount();
    },
    createSearchFilter() {
      let words = [];
      if (this.search) {
        words = this.search.toLowerCase().split(/ /);
      }
      function filter(item) {
        for (let word of words) {
          let match = false;
          if (item.title.toLowerCase().indexOf(word) >= 0) match = true;
          if (item.organization.short_name.toLowerCase().indexOf(word) >= 0)
            match = true;
          if (item.organization.name.toLowerCase().indexOf(word) >= 0)
            match = true;
          if (item.platform.name.toLowerCase().indexOf(word) >= 0) match = true;
          if (item.platform.short_name.toLowerCase().indexOf(word) >= 0)
            match = true;
          if (!match) {
            // no match for this word
            return false;
          }
        }
        return true;
      }
      return filter;
    },
  },

  watch: {
    showEditDialog(value) {
      if (!value) {
        this.selectedCredentials = null;
        this.loadSushiCredentialsCount();
      }
    },
    showCreateDialog(value) {
      if (!value) {
        this.selectedCredentials = null;
        this.loadSushiCredentialsCount();
      }
    },
    dataUrl() {
      this.loadSushiCredentialsList();
    },
  },
  mounted() {
    this.loadSushiCredentialsList();
  },
};
</script>

<style lang="scss"></style>
