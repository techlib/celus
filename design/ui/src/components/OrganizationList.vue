<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-data-table
    :items="visibleOrganizations"
    item-key="pk"
    :headers="headers"
    :items-per-page="-1"
    :sort-by="sortBy"
    :expanded="expanded"
    show-expand
    expand-icon="fa fa-caret-down"
    :search="search"
  >
    <template #top>
      <v-row>
        <v-col>
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
        <div class="py-2 d-inline-block">
          <TagCard
            scope="organization"
            :item-id="item.pk"
            @update="fetchTags"
            :elevation="0"
          />
        </div>
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
import { mapGetters, mapState } from "vuex";
import tags from "@/mixins/tags";
import TagSelector from "@/components/tags/TagSelector";
import TagCard from "@/components/tags/TagCard";
import TagChip from "@/components/tags/TagChip";
import { intersection } from "lodash";

export default {
  name: "OrganizationList",
  components: { TagChip, TagCard, TagSelector },
  mixins: [cancellation, tags],

  data() {
    return {
      sortBy: "name",
      expanded: [],
      search: "",
    };
  },

  computed: {
    ...mapState({
      organizationMap: "organizations",
    }),
    ...mapGetters({
      enableTags: "enableTags",
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
  },

  methods: {
    fetchTags() {
      if (this.organizations.length) {
        this.getTagsForObjectsById(
          "organization",
          this.organizations.map((item) => item.pk)
        );
      }
    },
  },

  mounted() {
    this.fetchTags();
  },

  watch: {
    organizations() {
      this.fetchTags();
    },
  },
};
</script>

<style scoped></style>
