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
  <v-skeleton-loader v-if="loading" type="table"></v-skeleton-loader>
  <v-data-table
    v-else
    :items="visibleOrganizations"
    item-key="pk"
    item-value="pk"
    :headers="headers"
    v-model:page="page"
    v-model:items-per-page="itemsPerPage"
    v-model:sort-by="orderBy"
    v-model:expanded="expanded"
    :search="search"
    class="auto-table"
  >
    <template #top>
      <v-row>
        <v-col>
          <TagSelector
            v-model="selectedTags"
            scope="organization"
            dont-check-exclusive
          ></TagSelector>
        </v-col>
        <v-spacer></v-spacer>
        <v-col>
          <v-text-field
            v-model="search"
            :label="$t('labels.search')"
            clearable
            clear-icon="fa fa-times"
          ></v-text-field>
        </v-col>
      </v-row>
    </template>
    <template v-slot:expanded-row="{ item, columns }">
      <tr class="item_expanded_space">
        <td></td>
        <td :colspan="columns.length + 1">
          <v-row class="py-2">
            <v-col>
              <div class="d-inline-block">
                <TagCard
                  scope="organization"
                  :item-id="item.pk"
                  @update="getTags"
                  :elevation="0"
                ></TagCard>
              </div>
            </v-col>
            <v-col>
              <v-list>
                <v-list-subheader class="sc caption font-weight-bold">
                  <v-tooltip location="bottom">
                    <template #activator="{ props }">
                      <span v-bind="props"
                        >{{ $t("aliases") }}
                        <v-icon size="small" color="info"
                          >fas fa-info-circle</v-icon
                        ></span
                      >
                    </template>
                    <span>{{ $t("aliases_tooltip") }}</span>
                  </v-tooltip>
                </v-list-subheader>
                <template v-for="e in item.alt_names" :key="e.pk">
                  <v-list-item
                    style="min-height: 32px"
                    :isActive="showManagementStuff"
                    :model-value="e.name"
                  >
                    <div class="d-flex align-center justify-space-between">
                      <v-list-item-title>{{ e.name }}</v-list-item-title>
                      <v-btn
                        size="x-small"
                        density="comfortable"
                        variant="outlined"
                        icon
                        color="error"
                        @click="deleteAlias(item.pk, e.pk)"
                        :loading="loadingDelete[item.pk]?.[e.pk]"
                      >
                        <v-icon size="x-small">fa fa-times</v-icon>
                      </v-btn>
                    </div>
                  </v-list-item>
                  <v-divider></v-divider>
                </template>
                <v-list-item v-if="showManagementStuff" isActive>
                  <div class="d-flex align-center">
                    <v-text-field
                      v-model="aliasAddInputs[item.pk]"
                      class="pt-0 mt-0"
                      :rules="[validateEmpty, validateExisting]"
                      :placeholder="$t('add_new_alias')"
                      @keydown.enter="createAlias(item.pk)"
                      :ref="'new-alias-' + item.pk"
                    ></v-text-field>
                    <v-btn
                      class="ml-3"
                      variant="outlined"
                      size="x-small"
                      icon
                      fab
                      color="success"
                      @click.stop="createAlias(item.pk)"
                      :loading="loadingCreate[item.pk]"
                      :disabled="
                        !aliasAddInputs[item.pk] ||
                        validateExisting(aliasAddInputs[item.pk]) != true ||
                        validateEmpty(aliasAddInputs[item.pk]) != true
                      "
                    >
                      <v-icon>fas fa-plus</v-icon>
                    </v-btn>
                  </div>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </td>
      </tr>
    </template>
    <template #item.tags="{ item }">
      <TagChip
        v-for="tag in objIdToTags.get(item.pk)"
        :key="tag.pk"
        :tag="tag"
        small
        show-class
      ></TagChip>
    </template>
  </v-data-table>
</template>

<v-icon
  color="warning"
  icon="fa-solid fa-triangle-exclamation"
  size="x-small"
></v-icon>

<script>
import TagCard from "@/components/tags/TagCard";
import TagChip from "@/components/tags/TagChip";
import TagSelector from "@/components/tags/TagSelector";
import cancellation from "@/mixins/cancellation";
import stateTracking from "@/mixins/stateTracking";
import tags from "@/mixins/tags";
import { intersection } from "lodash";
import { mapActions, mapGetters, mapState } from "vuex";

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
      orderBy: [{ key: "name", order: "asc" }],
      orderDesc: false,
      page: 1,
      itemsPerPage: 200,
      // state tracking support
      watchedAttrs: [
        {
          name: "orderBy",
          type: Object,
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
          title: this.$t("title_fields.short_name"),
          value: "short_name",
          key: "short_name",
          width: "10%",
        },
        {
          title: this.$t("title_fields.name"),
          value: "name",
          key: "name",
          width: "20%",
        },
      ];
      base.push({
        title: this.$i18n.t("labels.tags"),
        value: "tags",
        key: "tags",
        sortable: false,
      });
      base.unshift({
        title: "",
        value: "data-table-expand",
        sortable: false,
        align: "start",
        width: "5%",
      });
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
    getTags(tags, itemId) {
      this.objIdToTags.set(itemId, tags);
    },
    fetchTags() {
      if (this.organizations.length) {
        this.getTagsForObjectsById(
          "organization",
          this.organizations.map((item) => item.pk),
        );
      }
    },
    async deleteAlias(organization_pk, alias_pk) {
      // Don't validate empty create field when other alias is being deleted
      this.loadingDelete[organization_pk] =
        this.loadingDelete[organization_pk] || {};
      if (!this.aliasAddInputs[organization_pk]) {
        this.$refs[`new-alias-${organization_pk}`].resetValidation();
      }
      this.loadingDelete[organization_pk] || {};
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
        this.organizations.map((e) => [e.pk, ""]),
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
