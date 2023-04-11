<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  aliases: Aliases
  already_exists: Alias or organization with this name already exists.
  cant_be_empty: Alias can't be empty.
  aliases_tooltip: When importing usage data for multiple organizations from one file, aliases serve as alternative names for the organization.
  add_new_alias: Add new alias

cs:
  aliases: Aliasy
  already_exists: Alias nebo organizace s tímto jménem již existuje.
  cant_be_empty: Alias nemůže být prázdný.
  aliases_tooltip: Při importu dat pro více organizací z jednoho souboru slouží aliasy jako alternativní názvy pro organizaci.
  add_new_alias: Přidat nový alias
</i18n>

<template>
  <v-skeleton-loader v-if="loading" type="table" />
  <v-data-table
    v-else
    :items="visibleOrganizations"
    item-key="pk"
    :headers="headers"
    :page.sync="page"
    :items-per-page.sync="itemsPerPage"
    :sort-by.sync="orderBy"
    :sort-desc.sync="orderDesc"
    :expanded="expanded"
    :show-expand="enableTags"
    expand-icon="fa fa-caret-down"
    :search="search"
  >
    <template #top>
      <v-row>
        <v-col v-if="enableTags">
          <TagSelector
            v-model="selectedTags"
            scope="organization"
            dont-check-exclusive
          />
        </v-col>
        <v-spacer></v-spacer>
        <v-col>
          <v-text-field
            v-model="search"
            :label="$t('labels.search')"
            clearable
            clear-icon="fa-times"
          ></v-text-field>
        </v-col>
      </v-row>
    </template>
    <template #expanded-item="{ item, headers }">
      <td></td>
      <td :colspan="headers.length" v-if="enableTags">
        <v-row class="py-2">
          <v-col>
            <div class="d-inline-block">
              <TagCard
                scope="organization"
                :item-id="item.pk"
                @update="fetchTags"
                :elevation="0"
              />
            </div>
          </v-col>
          <v-col>
            <v-list>
              <v-subheader class="sc caption font-weight-bold">
                <v-tooltip bottom>
                  <template #activator="{ on }">
                    <span v-on="on"
                      >{{ $t("aliases") }}
                      <v-icon small color="info">fa-info-circle</v-icon></span
                    >
                  </template>
                  <span>{{ $t("aliases_tooltip") }}</span>
                </v-tooltip>
              </v-subheader>
              <template v-for="(e, index) in item.alt_names">
                <v-list-item
                  :value="e.name"
                  :key="e.pk"
                  style="min-height: 32px"
                >
                  <v-list-item-content>
                    <v-list-item-title v-text="e.name"></v-list-item-title>
                  </v-list-item-content>
                  <v-list-item-action v-if="showManagementStuff" class="my-0">
                    <v-btn
                      x-small
                      outlined
                      icon
                      color="error"
                      @click="deleteAlias(item.pk, e.pk)"
                      :loading="loadingDelete[item.pk]?.[e.pk]"
                    >
                      <v-icon x-small>fa-times</v-icon>
                    </v-btn>
                  </v-list-item-action>
                </v-list-item>
                <v-divider :key="'divider-' + index"></v-divider>
              </template>
              <v-list-item v-if="showManagementStuff">
                <v-list-item-content>
                  <v-text-field
                    v-model="aliasAddInputs[item.pk]"
                    class="pt-0 mt-0"
                    :rules="[validateEmpty, validateExisting]"
                    :placeholder="$t('add_new_alias')"
                    @keydown.enter="createAlias(item.pk)"
                    :ref="'new-alias-' + item.pk"
                  ></v-text-field>
                </v-list-item-content>
                <v-list-item-action class="my-0">
                  <v-btn
                    x-small
                    outlined
                    fab
                    color="success"
                    @click="createAlias(item.pk)"
                    :loading="loadingCreate[item.pk]"
                    :disabled="
                      !aliasAddInputs[item.pk] ||
                      validateExisting(aliasAddInputs[item.pk]) != true ||
                      validateEmpty(aliasAddInputs[item.pk]) != true
                    "
                  >
                    <v-icon>fa-plus</v-icon>
                  </v-btn>
                </v-list-item-action>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>
      </td>
    </template>
    <template #item.tags="{ item }">
      <TagChip
        v-for="tag in objIdToTags.get(item.pk)"
        :key="tag.pk"
        :tag="tag"
        small
        show-class
      />
    </template>
  </v-data-table>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import { mapActions, mapGetters, mapState } from "vuex";
import tags from "@/mixins/tags";
import TagSelector from "@/components/tags/TagSelector";
import TagCard from "@/components/tags/TagCard";
import TagChip from "@/components/tags/TagChip";
import { intersection } from "lodash";
import stateTracking from "@/mixins/stateTracking";

export default {
  name: "OrganizationList",
  components: { TagChip, TagCard, TagSelector },
  mixins: [cancellation, tags, stateTracking],

  data() {
    return {
      expanded: [],
      search: "",
      loading: true,
      // table state
      orderBy: "name",
      orderDesc: false,
      page: 1,
      itemsPerPage: -1,
      // state tracking support
      watchedAttrs: [
        {
          name: "orderBy",
          type: String,
        },
        {
          name: "orderDesc",
          type: Boolean,
        },
        {
          name: "page",
          type: Number,
        },
        {
          name: "itemsPerPage",
          type: Number,
          var: "ipp",
        },
        {
          name: "search",
          type: String,
        },
        {
          name: "selectedTags",
          type: Object,
        },
      ],
      aliasAddInputs: {},
      loadingCreate: {},
      loadingDelete: {},
      createForms: {},
    };
  },

  computed: {
    ...mapState({
      organizationMap: "organizations",
    }),
    ...mapGetters({
      enableTags: "enableTags",
      showManagementStuff: "showManagementStuff",
    }),
    organizations() {
      return Object.values(this.organizationMap).filter((item) => item.pk > 0);
    },
    visibleOrganizations() {
      if (this.selectedTags.length) {
        return this.organizations.filter((org) => {
          if (this.objIdToTags.has(org.pk)) {
            const objTagIds = this.objIdToTags.get(org.pk).map((tag) => tag.pk);
            return intersection(this.selectedTags, objTagIds).length > 0;
          } else {
            return false;
          }
        });
      }
      return this.organizations;
    },
    headers() {
      let base = [
        {
          text: this.$t("title_fields.short_name"),
          value: "short_name",
        },
        {
          text: this.$t("title_fields.name"),
          value: "name",
        },
      ];
      if (this.enableTags) {
        base.push({
          text: this.$i18n.t("labels.tags"),
          value: "tags",
        });
      }
      return base;
    },
    nameMap() {
      let result = {};
      for (const org of this.organizations) {
        result[org.short_name] = org;
        result[org.name] = org;
        for (const altname of org.alt_names) {
          result[altname.name] = org;
        }
      }
      return result;
    },
  },

  methods: {
    ...mapActions({
      loadOrganizations: "loadOrganizations",
      showSnackbar: "showSnackbar",
    }),
    fetchTags() {
      if (this.organizations.length) {
        this.getTagsForObjectsById(
          "organization",
          this.organizations.map((item) => item.pk)
        );
      }
    },
    async deleteAlias(organization_pk, alias_pk) {
      // Don't validate empty create field when other alias is being deleted
      if (!this.aliasAddInputs[organization_pk]) {
        this.$refs[`new-alias-${organization_pk}`].resetValidation();
      }

      this.loadingDelete[organization_pk] ||= {};
      this.loadingDelete[organization_pk][alias_pk] = true;
      let result = await this.http({
        url: `/api/organization/${organization_pk}/alt-names/${alias_pk}`,
        method: "delete",
      });
      if (result.error) {
        this.showSnackbar({ content: "Error deleting alias: " + result.error });
      } else {
        await this.loadOrganizations();
      }
      if (this.loadingDelete[organization_pk]) {
        this.loadingDelete[organization_pk][alias_pk] = false;
      }
    },
    async createAlias(organization_pk) {
      if (
        this.validateExisting(this.aliasAddInputs[organization_pk]) != true ||
        this.validateEmpty(this.aliasAddInputs[organization_pk]) != true
      ) {
        // 'enter' was hit while editing, but the input is invalid -> suppress it
        // force validation of the text field (the validation is hidden after
        // a successful object creation, so we need to re-display it)
        this.$refs[`new-alias-${organization_pk}`].validate(true);
        return;
      }
      this.loadingCreate[organization_pk] = true;
      let result = await this.http({
        url: `/api/organization/${organization_pk}/alt-names/`,
        method: "post",
        data: { name: this.aliasAddInputs[organization_pk] },
      });
      if (result.error) {
        this.showSnackbar({ content: "Error creating alias: " + result.error });
      } else {
        this.aliasAddInputs[organization_pk] = "";
        this.$refs[`new-alias-${organization_pk}`].resetValidation();
        await this.loadOrganizations();
      }
      this.loadingCreate[organization_pk] = false;
    },
    init() {
      this.aliasAddInputs = Object.fromEntries(
        this.organizations.map((e) => [e.pk, ""])
      );
      this.loadingCreate = {};
      this.loadingDelete = {};
    },
    validateExisting(new_name) {
      if (this.nameMap[new_name]) {
        return this.$t("already_exists");
      } else {
        return true;
      }
    },
    validateEmpty(new_name) {
      if (new_name === null || new_name.trim() === "") {
        return this.$t("cant_be_empty");
      } else {
        return true;
      }
    },
  },

  mounted() {
    this.fetchTags();
    this.init();
    this.loading = false;
  },

  watch: {
    organizations() {
      this.fetchTags();
      this.init();
    },
  },
};
</script>

<style scoped></style>
