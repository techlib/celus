<i18n lang="yaml">
en:
  database_connection:
    title: Database Connection Information
    host: Host
    port: Port
    port_value: 9440 (TCP) or 8443 (HTTPS) - select the one that works for your client
    database: Database
    username: Username
    password: Password
    tls: TLS/SSL
    tls_enabled: Required
    info: Use these credentials to connect to the ClickHouse database. TLS/SSL must be enabled. The password is a sensitive information - keep it secure and do not share it with unauthorized persons.
  password_modal:
    title: Password
    warning: This is your password for the database. Keep it secret and do not share it with unauthorized persons.
    close: Close
  test_link_text: You can test the connection to the database using {test_link}. It will open a web interface of the database with a sample query.
  test_link: this link
  start_export: Start Sync Manually
  export_running: Sync is currently running
  export_available_in: To prevent excessive load on the database, sync cannot be run too frequently. Next manual sync will be available in {time}.
  export_not_available: Sync is not available yet
  export_started: Sync started successfully
  export_start_failed: Failed to start synchronization

cs:
  database_connection:
    title: Informace o připojení k databázi
    host: Hostitel
    port: Port
    port_value: 9440 (TCP) nebo 8443 (HTTPS) - vyberte ten, který funguje pro váš klient
    database: Databáze
    username: Uživatelské jméno
    password: Heslo
    tls: TLS/SSL
    tls_enabled: Povinné
    info: Použijte tyto přihlašovací údaje pro připojení k databázi ClickHouse. TLS/SSL musí být zapnuto. Heslo je citlivá informace - uchovávejte ho v bezpečí a nesdílejte ho s neoprávněnými osobami.
  password_modal:
    title: Heslo
    warning: Toto je vaše heslo pro databázi. Uchovávejte ho v tajnosti a nesdílejte ho s neoprávněnými osobami.
    close: Zavřít
  test_link_text: Můžete otestovat připojení k databázi pomocí {test_link}. Otevře se webové rozhraní databáze s ukázkovým dotazem.
  test_link: tohoto odkazu
  start_export: Spustit synchronizaci manuálně
  export_running: Export právě běží
  export_available_in: Pro omezení zatížení databáze synchronizace nelze spouštět příliš často. Další synchronizace bude dostupná za {time}.
  export_not_available: Synchronizace ještě není dostupná
  export_started: Synchronizace úspěšně spuštěna
  export_start_failed: Nepodařilo se spustit export
</i18n>

<template>
  <v-card class="ma-4" elevation="0" style="border-color: #e0e0e0">
    <v-card-title class="text-h6">
      <v-icon class="me-2" color="grey" size="x-small">fa fa-database</v-icon>
      {{ $t("database_connection.title") }}
    </v-card-title>
    <v-card-text>
      <v-table density="compact" class="mb-4">
        <tbody>
          <tr>
            <td class="text-subtitle-2 font-weight-medium" style="width: 200px">
              {{ $t("database_connection.host") }}
            </td>
            <td class="font-family-monospace">
              <div class="d-flex align-center">
                <span class="flex-grow-0">{{ clickhouseExportHost }}</span>
                <CopyToClipboardButton
                  :value="clickhouseExportHost"
                  class="ml-2"
                />
              </div>
            </td>
          </tr>
          <tr>
            <td class="text-subtitle-2 font-weight-medium">
              {{ $t("database_connection.port") }}
            </td>
            <td class="font-family-monospace">
              {{ $t("database_connection.port_value") }}
            </td>
          </tr>
          <tr>
            <td class="text-subtitle-2 font-weight-medium">
              {{ $t("database_connection.database") }}
            </td>
            <td class="font-family-monospace">
              <div class="d-flex align-center">
                <span class="flex-grow-0">{{ exportObj.ch_database }}</span>
                <CopyToClipboardButton
                  :value="exportObj.ch_database"
                  class="ml-2"
                />
              </div>
            </td>
          </tr>
          <tr>
            <td class="text-subtitle-2 font-weight-medium">
              {{ $t("database_connection.username") }}
            </td>
            <td class="font-family-monospace">
              <div class="d-flex align-center">
                <span class="flex-grow-0">{{ exportObj.ch_database }}</span>
                <CopyToClipboardButton
                  :value="exportObj.ch_database"
                  class="ml-2"
                />
              </div>
            </td>
          </tr>
          <tr>
            <td class="text-subtitle-2 font-weight-medium">
              {{ $t("database_connection.password") }}
            </td>
            <td>
              <div class="d-flex align-center">
                <v-btn
                  @click="handleShowPassword"
                  variant="text"
                  size="small"
                  icon="fa fa-eye"
                  color="primary"
                />
              </div>
            </td>
          </tr>
          <tr>
            <td class="text-subtitle-2 font-weight-medium">
              {{ $t("database_connection.tls") }}
            </td>
            <td>
              <v-chip color="success" size="small" variant="flat" class="px-4">
                <v-icon start size="x-small">fa fa-lock</v-icon>
                {{ $t("database_connection.tls_enabled") }}
              </v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-alert type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>fa fa-info-circle</v-icon>
        </template>
        {{ $t("database_connection.info") }}
      </v-alert>

      <div class="mt-8 d-flex align-center">
        <v-btn
          @click="startExport"
          :disabled="!exportObj.can_start_export || startingExport"
          :loading="startingExport"
          color="primary"
        >
          <v-icon start size="x-small">fa fa-cloud-arrow-up</v-icon>
          {{ $t("start_export") }}
        </v-btn>
        <v-tooltip
          v-if="!exportObj.can_start_export"
          location="bottom"
          :text="availabilityMessage"
        >
          <template #activator="{ props }">
            <v-icon v-bind="props" class="ml-2" color="grey"
              >fa fa-info-circle</v-icon
            >
          </template>
        </v-tooltip>
      </div>

      <ChExportBatchReportTypes
        v-if="exportObj.latest_batch"
        :batch-id="exportObj.latest_batch.id"
        :ch-database="exportObj.ch_database"
        :ch-password="exportObj.ch_password"
        @batch-finished="handleBatchFinished"
      />
    </v-card-text>
  </v-card>

  <!-- Password Modal Dialog -->
  <v-dialog v-model="passwordModal" max-width="500">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="me-2" size="x-small" color="grey">fa fa-key</v-icon>
        {{ $t("password_modal.title") }}
      </v-card-title>

      <v-card-text>
        <div class="mb-4">
          <p class="text-body-2">
            {{ $t("password_modal.warning") }}
          </p>
        </div>

        <div
          class="d-flex align-center pa-3 border rounded"
          style="cursor: pointer"
        >
          <span class="font-family-monospace flex-grow-1">{{
            selectedPassword
          }}</span>
          <CopyToClipboardButton :value="selectedPassword" />
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="passwordModal = false" variant="text">
          {{ $t("password_modal.close") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import ChExportBatchReportTypes from "@/components/ch-export/ChExportBatchReportTypes.vue";
import CopyToClipboardButton from "@/components/util/CopyToClipboardButton.vue";
import cancellation from "@/mixins/cancellation";
import { formatDuration, intervalToDuration } from "date-fns";
import { mapActions, mapGetters } from "vuex";

export default {
  name: "ChExportDatabaseConnectionCard",

  emits: ["export-started", "export-finished"],

  components: {
    ChExportBatchReportTypes,
    CopyToClipboardButton,
  },
  mixins: [cancellation],

  props: {
    exportObj: {
      type: Object,
      required: true,
    },
  },

  data() {
    return {
      passwordModal: false,
      selectedPassword: "",
      startingExport: false,
    };
  },

  computed: {
    ...mapGetters({
      clickhouseExportHost: "clickhouseExportHost",
    }),
    testLinkValue() {
      return this.testLink(this.exportObj);
    },
    availabilityMessage() {
      if (!this.exportObj.next_export_available_at) {
        if (this.exportObj.status === "running") {
          return this.$t("export_running");
        }
        return this.$t("export_not_available");
      }
      const availableAt = new Date(this.exportObj.next_export_available_at);
      const now = new Date();
      const duration = intervalToDuration({ start: now, end: availableAt });
      const timeString = formatDuration(duration, {
        format: ["hours", "minutes"],
      });

      return this.$t("export_available_in", { time: timeString });
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    showPasswordModal(password) {
      this.selectedPassword = password;
      this.passwordModal = true;
    },
    handleShowPassword() {
      this.showPasswordModal(this.exportObj.ch_password);
    },
    handleBatchFinished() {
      // Emit event to parent to reload data when batch finishes
      this.$emit("export-finished");
    },
    async startExport() {
      this.startingExport = true;
      const { response, error } = await this.http({
        url: `/api/ch-export/exports/${this.exportObj.id}/start_export/`,
        method: "post",
        dontShowError: true,
      });
      if (error) {
        let errorMessage = this.$t("export_start_failed");
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        }
        this.showSnackbar({
          content: errorMessage,
          color: "error",
        });
      } else if (response) {
        this.showSnackbar({
          content: this.$t("export_started"),
          color: "success",
        });
        // Emit event to parent to reload data
        this.$emit("export-started");
      }
      this.startingExport = false;
    },
    testLink(exportItem) {
      // create a link to the TR table with a sample query
      for (const rt of ["TR", "TR51"]) {
        if (
          exportItem.latest_batch &&
          exportItem.latest_batch.report_types.includes(rt)
        ) {
          let query =
            `SELECT platform__name, SUM(value) AS Unique_Item_Requests FROM ${rt} WHERE ` +
            `metric__short_name='Unique_Item_Requests' GROUP BY 1 ORDER BY 2 DESC LIMIT 50;`;
          // the url contains the query as a base64 encoded string
          let base64Query = btoa(query);
          let url =
            `https://${this.clickhouseExportHost}:8443/play?user=${exportItem.ch_database}` +
            `&password=${exportItem.ch_password}&run=1` +
            `&url=https%3A%2F%2F${this.clickhouseExportHost}%3A8443%2F%3Fdatabase%3D${exportItem.ch_database}` +
            `#${base64Query}`;
          return url;
        }
      }
      return null;
    },
  },
};
</script>
