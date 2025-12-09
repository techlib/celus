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
  no_exports_found: Analytical database export is not configured for this organization. Please contact us at {email} to have it set up.
  info_text: |
    Analytical database export is a powerful feature for those of you who want to analyze the data stored in CELUS themselves.
  info_text_2: |
    The data is exported regularly into a powerful dedicated analytical database {chLink} running on our infrastructure.
    It is a suitable source for ingestion into Power BI, Superset, Metabase and other analytical tools.
  info_text_3: |
    You can read more about this feature in our {link}.
  info_text_beta: |
    This feature is currently in beta. Please contact us at {email} if you would like to test it.
  info_link_text: documentation

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
  no_exports_found: Export do analytické databáze není pro tuto organizaci nastaven. Kontaktujte nás na {email}, pokud ji chcete otestovat.
  info_text: |
    Export do analytické databáze je výkonná funkce pro ty z vás, kteří chtějí analyzovat data uložená v CELUSu sami.
  info_text_2: |
    Data jsou exportována pravidelně do výkonné dedikované analytické databáze {chLink} běžící na naší infrastruktuře.
    Je vhodným zdrojem pro propojení do Power BI, Superset, Metabase a dalších analytických nástrojů.
  info_text_3: |
    Více informací o této funkci naleznete v naší {link}.
  info_link_text: dokumentaci
  info_text_beta: |
    Tato funkce je momentálně ve fázi beta. Kontaktujte nás na {email}, pokud ji chcete vyzkoušet.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h1>{{ $t("title") }}</h1>

        <v-alert variant="tonal" class="ma-4">
          <p class="mb-2">{{ $t("info_text") }}</p>

          <i18n-t keypath="info_text_2" tag="p" class="mb-2">
            <template #chLink>
              <a
                href="https://clickhouse.com/"
                target="_blank"
                class="text-info active_link"
                >Clickhouse</a
              >
            </template>
          </i18n-t>
          <i18n-t keypath="info_text_3" tag="p" class="mb-2">
            <template #link>
              <a
                href="https://docs.celus.net/analytical-database.html"
                target="_blank"
                class="text-info active_link"
              >
                {{ $t("info_link_text") }}
              </a>
            </template>
          </i18n-t>

          <i18n-t
            keypath="info_text_beta"
            tag="p"
            class="mt-2"
            v-if="!exports.length"
          >
            <template #email>
              <a :href="`mailto:${contactEmail}`" class="text-info active_link">
                {{ contactEmail }}
              </a>
            </template>
          </i18n-t>
        </v-alert>

        <v-card>
          <v-card-title>
            <v-btn @click="loadData" :loading="loading" color="primary">
              <v-icon start size="x-small">fa fa-refresh</v-icon>
              {{ $t("refresh") }}
            </v-btn>
          </v-card-title>

          <div v-if="!showManagementStuff">
            <ChExportDatabaseConnectionCard
              v-if="!loading && exports.length > 0"
              :export-obj="exports[0]"
              @export-finished="loadData"
              @export-started="loadData"
            />
            <div v-else-if="loading" class="text-center">
              <v-progress-circular indeterminate color="primary" />
            </div>
            <div v-else class="text-center">
              <v-alert type="info" variant="tonal" class="ma-4">
                {{ $t("no_exports_found", { email: contactEmail }) }}
              </v-alert>
            </div>
          </div>
          <v-data-table
            v-else
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
                  <ChExportDatabaseConnectionCard
                    :export-obj="item"
                    @export-finished="loadData"
                    @export-started="loadData"
                  />
                </td>
              </tr>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import ChExportDatabaseConnectionCard from "@/components/ch-export/ChExportDatabaseConnectionCard.vue";
import cancellation from "@/mixins/cancellation";
import { format } from "date-fns";
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "ExportTasksPage",
  components: {
    ChExportDatabaseConnectionCard,
  },
  mixins: [cancellation],

  data() {
    return {
      exports: [],
      loading: false,
      search: "",
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
      showManagementStuff: "showManagementStuff",
      contactEmail: "contactEmail",
    }),
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    url() {
      // when normal user is viewing one organization, we only want to show the
      // export for that organization;
      // for managers, we want to show all exports - regardless of organization;
      if (this.showManagementStuff) {
        return "/api/ch-export/exports/";
      }
      if (this.organizationId) {
        return `/api/ch-export/exports/?organization=${this.organizationId}`;
      }
      return null;
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadData() {
      if (!this.url) {
        this.exports = [];
        return;
      }
      this.loading = true;
      const { response, error } = await this.http({
        url: this.url,
        dontShowError: true,
      });
      if (error) {
        this.showSnackbar({
          content: this.$t("error_loading"),
          color: "error",
        });
      } else if (response) {
        this.exports = response.data;
      }
      this.loading = false;
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
  },

  watch: {
    url: {
      immediate: true,
      handler() {
        if (this.url) {
          this.loadData();
        }
      },
    },
  },
};
</script>
