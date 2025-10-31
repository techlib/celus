<i18n lang="yaml">
en:
  title: Analytical database configuration
  search: Search exports...
  refresh: Refresh
  error_loading: Failed to load exports
  collapse: Collapse
  more_info: More info
  headers:
    organization: Organization
    status: Status
    last_sync: Last Sync
    ch_database: Database
    ch_username: User name
    ch_password: Password
    consortial_full_export: "Consortial full export"
  status:
    empty: Empty (no access logs found)
    running: Running
    completed: Completed
    failed: Failed
  password_modal:
    title: Password
    warning: This is your password for the database. Keep it secret and do not share it with unauthorized persons.
    close: Close
    copied: Password copied to clipboard
    copy_failed: Failed to copy password
  database_connection:
    title: Database Connection Information
    host: Host
    port: Port
    port_value: 9440 (TCP) or 8443 (HTTPS)
    database: Database
    username: Username
    password: Password
    tls: TLS/SSL
    tls_enabled: Required
    info: Use these credentials to connect to the ClickHouse database. TLS/SSL must be enabled for secure connections. The password is sensitive information - keep it secure and do not share it with unauthorized persons.
  report_types: Report tables from last sync
  test_link_text: You can test the connection to the database using {test_link}. It will open a web interface of the database with a sample query.
  test_link: this link

cs:
  title: Konfigurace analytické databáze
  search: Hledat exporty...
  refresh: Obnovit
  error_loading: Nepodařilo se načíst exporty
  collapse: Sbalit
  more_info: Více informací
  headers:
    organization: Organizace
    status: Stav
    last_sync: Poslední synchronizace
    ch_database: Jméno databáze
    ch_username: Jméno uživatele
    ch_password: Heslo
    consortial_full_export: "Celkový export pro konzorcium"
  status:
    error: Prázdný (žádné záznamy nenalezeny)
    running: Běží
    completed: Dokončeno
    failed: Selhalo
  password_modal:
    title: Heslo
    warning: Toto je vaše heslo pro databázi. Uchovávejte ho v tajnosti a nesdílejte ho s neoprávněnými osobami.
    close: Zavřít
    copied: Heslo zkopírováno do schránky
    copy_failed: Nepodařilo se zkopírovat heslo
  database_connection:
    title: Informace o připojení k databázi
    host: Hostitel
    port: Port
    port_value: 9440 (TCP) nebo 8443 (HTTPS)
    database: Databáze
    username: Uživatelské jméno
    password: Heslo
    tls: TLS/SSL
    tls_enabled: Povinné
    info: Použijte tyto přihlašovací údaje pro připojení k databázi ClickHouse. TLS/SSL musí být povoleno pro bezpečná připojení. Heslo je citlivá informace - uchovávejte ho v bezpečí a nesdílejte ho s neoprávněnými osobami.
  report_types: Tabulky reportů z poslední synchronizace
  test_link_text: Můžete otestovat připojení k databázi pomocí {test_link}. Otevře se webové rozhraní databáze s ukázkovým dotazem.
  test_link: tohoto odkazu
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h1>{{ $t("title") }}</h1>
        <v-card>
          <v-card-title>
            <v-btn @click="loadData" :loading="loading" color="primary">
              {{ $t("refresh") }}
            </v-btn>
          </v-card-title>

          <v-data-table
            :headers="headers"
            :items="exports"
            :loading="loading"
            :search="search"
            item-value="id"
            show-expand
          >
            <template #item.organization="{ item }">
              <template v-if="item.organization">
                {{ item.organization }}
              </template>
              <template v-else>
                <span class="font-italic">{{
                  $t("headers.consortial_full_export")
                }}</span></template
              >
            </template>

            <template #item.status="{ item }">
              <v-chip
                :color="getStatusColor(item.status)"
                v-if="item.status"
                variant="flat"
                size="small"
              >
                {{ $t(`status.${item.status}`) }}
              </v-chip>
              <template v-else>-</template>
            </template>

            <template #item.last_sync="{ item }">
              {{ item.last_sync ? formatDateTime(item.last_sync) : "-" }}
            </template>

            <template
              #item.data-table-expand="{
                internalItem,
                isExpanded,
                toggleExpand,
              }"
            >
              <v-btn
                :append-icon="
                  isExpanded(internalItem)
                    ? 'fa fa-chevron-up'
                    : 'fa fa-chevron-down'
                "
                :text="
                  isExpanded(internalItem) ? $t('collapse') : $t('more_info')
                "
                class="text-none"
                color="medium-emphasis"
                size="small"
                variant="text"
                slim
                border
                @click="toggleExpand(internalItem)"
              ></v-btn>
            </template>

            <template #expanded-row="{ item }">
              <tr>
                <td :colspan="headers.length">
                  <v-card
                    class="ma-4"
                    elevation="0"
                    style="border-color: #e0e0e0"
                  >
                    <v-card-title class="text-h6">
                      <v-icon class="me-2" color="grey" size="x-small"
                        >fa fa-database</v-icon
                      >
                      {{ $t("database_connection.title") }}
                    </v-card-title>
                    <v-card-text>
                      <v-table density="compact" class="mb-4">
                        <tbody>
                          <tr>
                            <td
                              class="text-subtitle-2 font-weight-medium"
                              style="width: 200px"
                            >
                              {{ $t("database_connection.host") }}
                            </td>
                            <td class="font-family-monospace">
                              {{ clickhouseExportHost }}
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
                              {{ item.ch_database }}
                            </td>
                          </tr>
                          <tr>
                            <td class="text-subtitle-2 font-weight-medium">
                              {{ $t("database_connection.username") }}
                            </td>
                            <td class="font-family-monospace">
                              {{ item.ch_database }}
                            </td>
                          </tr>
                          <tr>
                            <td class="text-subtitle-2 font-weight-medium">
                              {{ $t("database_connection.password") }}
                            </td>
                            <td>
                              <div class="d-flex align-center">
                                <v-btn
                                  @click="showPasswordModal(item.ch_password)"
                                  variant="text"
                                  size="small"
                                  icon="fa fa-eye"
                                  color="primary"
                                  class="ml-2"
                                />
                              </div>
                            </td>
                          </tr>
                          <tr>
                            <td class="text-subtitle-2 font-weight-medium">
                              {{ $t("database_connection.tls") }}
                            </td>
                            <td>
                              <v-chip
                                color="success"
                                size="small"
                                variant="flat"
                                class="px-4"
                              >
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

                      <h3 class="text-h6 mt-8 mb-4" v-if="item.latest_batch">
                        <v-icon class="me-2" color="grey" size="x-small"
                          >fa fa-table</v-icon
                        >
                        {{ $t("report_types") }}
                      </h3>
                      <div v-if="item.latest_batch">
                        <v-chip
                          v-for="report_type in item.latest_batch.report_types"
                          :key="report_type"
                          class="me-1"
                          label
                        >
                          {{ report_type }}
                        </v-chip>
                      </div>
                      <div
                        v-if="testLink(item)"
                        class="mt-4 text-medium-emphasis"
                      >
                        <i18n-t keypath="test_link_text" tag="p">
                          <template #test_link>
                            <a
                              :href="testLink(item)"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {{ $t("test_link") }}
                            </a>
                          </template>
                        </i18n-t>
                      </div>
                    </v-card-text>
                  </v-card>
                </td>
              </tr>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

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
            @click="copyPassword"
            style="cursor: pointer"
          >
            <span class="font-family-monospace flex-grow-1">{{
              selectedPassword
            }}</span>
            <v-btn
              icon="fa fa-copy"
              size="small"
              variant="text"
              color="grey"
              :loading="copying"
              @click.stop="copyPassword"
            />
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
  </v-container>
</template>

<script>
import axios from "axios";
import { format } from "date-fns";
import { mapActions, mapGetters } from "vuex";

export default {
  name: "ExportTasksPage",

  data() {
    return {
      exports: [],
      loading: false,
      search: "",
      passwordModal: false,
      selectedPassword: "",
      copying: false,
      headers: [
        {
          title: this.$t("headers.organization"),
          key: "organization",
          sortable: true,
        },
        { title: this.$t("headers.status"), key: "status", sortable: true },
        {
          title: this.$t("headers.last_sync"),
          key: "last_sync",
          sortable: true,
        },
        {
          title: this.$t("headers.ch_database"),
          key: "ch_database",
          sortable: false,
        },
      ],
    };
  },

  computed: {
    ...mapGetters({
      clickhouseExportHost: "clickhouseExportHost",
    }),
  },

  mounted() {
    this.loadData();
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadData() {
      this.loading = true;
      try {
        const response = await axios.get("/api/ch-export/exports/");
        this.exports = response.data.results || response.data;
      } catch (error) {
        console.error("Error loading exports:", error);
        this.showSnackbar({
          content: this.$t("error_loading"),
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },

    getStatusColor(status) {
      const colors = {
        empty: "grey",
        running: "blue",
        completed: "green",
        failed: "red",
      };
      return colors[status] || "grey";
    },

    formatDateTime(dateString) {
      if (!dateString) return "-";
      return format(new Date(dateString), "yyyy-MM-dd HH:mm:ss");
    },

    showPasswordModal(password) {
      this.selectedPassword = password;
      this.passwordModal = true;
    },

    async copyPassword() {
      this.copying = true;
      try {
        await navigator.clipboard.writeText(this.selectedPassword);
        this.showSnackbar({
          content: this.$t("password_modal.copied"),
          color: "success",
        });
      } catch (error) {
        console.error("Failed to copy password:", error);
        this.showSnackbar({
          content: this.$t("password_modal.copy_failed"),
          color: "error",
        });
      } finally {
        this.copying = false;
      }
    },

    testLink(item) {
      // create a link to the TR table with a sample query
      for (const rt of ["TR", "TR51"]) {
        if (item.latest_batch && item.latest_batch.report_types.includes(rt)) {
          let query =
            `SELECT platform__name, SUM(value) AS Unique_Item_Requests FROM ${rt} WHERE ` +
            `metric__short_name='Unique_Item_Requests' GROUP BY 1 ORDER BY 2 DESC LIMIT 50;`;
          // the url contains the query as a base64 encoded string
          let base64Query = btoa(query);
          let url =
            `https://${this.clickhouseExportHost}:8443/play?user=${item.ch_database}` +
            `&password=${item.ch_password}&run=1` +
            `&url=https%3A%2F%2F${this.clickhouseExportHost}%3A8443%2F%3Fdatabase%3D${item.ch_database}` +
            `#${base64Query}`;
          return url;
        }
      }
      return null;
    },
  },
};
</script>
