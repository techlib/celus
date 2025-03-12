<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml" src="@/locales/annotations.yaml"></i18n>

<i18n lang="yaml">
en:
  columns:
    created: Created
  are_you_sure: "Are you sure to delete {0}?"

cs:
  columns:
    created: Vytvořeno
  are_you_sure: "Určitě chcete smazat {0}?"
</i18n>

<template>
  <v-row>
    <v-col>
      <v-data-table
        :items="annotations"
        density="default"
        :headers="headers"
        :sort-by="[{ key: 'pk', order: 'asc' }]"
        item-key="pk"
        item-value="pk"
        :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
        :options="options"
        :loading="loading"
        :page="page"
        :items-per-page="10"
        :server-items-length="serverItemsLength"
        v-model:expanded="expandedRows"
        class="auto-table"
      >
        <template v-slot:top>
          <v-dialog
            v-model="showEditDialog"
            max-width="1240px"
            @click:outside="cancelEdit"
          >
            <v-card>
              <v-card-title>{{ $t("actions.edit") }}</v-card-title>
              <v-card-text>
                <AnnotationCreateModifyWidget
                  ref="widget"
                  :annotation="selectedAnnotation"
                  @saved="annotationSaved"
                  @cancel="cancelEdit"
                  :showDeleteButton="false"
                ></AnnotationCreateModifyWidget>
              </v-card-text>
            </v-card>
          </v-dialog>
          <v-dialog v-model="showDeleteDialog" max-width="620px">
            <v-card>
              <v-card-title>{{ $t("actions.delete") }}</v-card-title>
              <v-card-text>
                <i18n-t keypath="are_you_sure" tag="p">
                  <span class="font-weight-bold"
                    >{{ selectedAnnotation[`subject_${lang}`] }}
                  </span>
                </i18n-t>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                  @click="cancelDelete()"
                  variant="flat"
                  elevation="2"
                  color="defaultButton"
                  >{{ $t("cancel") }}</v-btn
                >
                <v-btn
                  variant="flat"
                  elevation="2"
                  @click="deleteAnnotation()"
                  color="error"
                >
                  <v-icon size="small" class="mr-2">fa fa-trash</v-icon>
                  {{ $t("actions.delete") }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </template>
        <template #item.level="{ item }">
          <v-tooltip location="bottom" v-if="item.level == 'info'">
            <template v-slot:activator="{ props }">
              <v-icon size="small" class="mr-2" color="blue" v-bind="props">
                fas fa-info-circle
              </v-icon>
            </template>
            <span v-text="$t('annotations.labels.level_info')"></span>
          </v-tooltip>
          <v-tooltip location="bottom" v-if="item.level == 'important'">
            <template v-slot:activator="{ props }">
              <v-icon size="small" class="mr-2" color="orange" v-bind="props">
                fas fa-exclamation-triangle
              </v-icon>
            </template>
            <span v-text="$t('annotations.labels.level_important')"></span>
          </v-tooltip>
        </template>
        <template #item.actions="{ item }">
          <v-icon
            v-if="item.can_edit"
            size="small"
            class="mr-2"
            @click="editItem(item)"
            color="lighterIcons"
          >
            fas fa-pen
          </v-icon>
          <v-icon
            v-if="item.can_edit"
            size="small"
            class="mr-2"
            @click="deleteItem(item)"
            color="lighterIcons"
          >
            fas fa-trash-alt
          </v-icon>
        </template>
        <template v-slot:expanded-row="{ item, columns }">
          <tr class="item_expanded_space">
            <td :colspan="columns.length" class="py-3">
              <div class="caption">
                {{ $t("annotations.labels.date_range") }}
              </div>
              <div class="pb-2">{{ item.start_date }}–{{ item.end_date }}</div>
              <div class="caption">
                {{ $t("annotations.labels.short_message") }}
              </div>
              <div class="pb-2">
                {{ item.short_message || $t("annotations.messages.empty") }}
              </div>
              <div class="caption">
                {{ $t("annotations.labels.message") }}
              </div>
              <div>
                {{
                  item.message.length
                    ? item.message
                    : $t("annotations.messages.empty")
                }}
              </div>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-col>
  </v-row>
</template>

<script>
import AnnotationCreateModifyWidget from "./AnnotationCreateModifyWidget.vue";
import cancellation from "@/mixins/cancellation";
import { mapState } from "vuex";

export default {
  name: "AnnotationList",

  mixins: [cancellation],

  props: {
    loading: {
      type: Boolean,
      required: true,
    },
    annotations: {
      type: Array,
      required: true,
    },
    page: {
      type: Number,
      required: true,
    },
    serverItemsLength: {
      type: Number,
      required: true,
    },
  },

  components: {
    AnnotationCreateModifyWidget,
  },

  data() {
    return {
      selectedAnnotation: {},
      showEditDialog: false,
      showDeleteDialog: false,
      options: {},
      expandedRows: [],
    };
  },

  computed: {
    ...mapState({
      lang: "appLanguage",
      organization: "selectedOrganizationId",
    }),
    headers() {
      return [
        {
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
          width: "3%",
        },
        {
          title: this.$i18n.t("annotations.labels.subject"),
          value: `subject_${this.lang}`,
          key: `subject_${this.lang}`,
        },
        {
          title: this.$i18n.t("organization"),
          value: `organization.name_${this.lang}`,
          key: `organization.name_${this.lang}`,
        },
        {
          title: this.$i18n.t("platform"),
          value: "platform.name",
          key: "platform.name",
        },
        {
          title: this.$i18n.t("annotations.labels.level"),
          value: "level",
          align: "center",
          key: "level",
        },
        {
          title: this.$i18n.t("annotations.labels.author"),
          value: "author",
          key: "author",
        },
        {
          title: this.$i18n.t("title_fields.actions"),
          value: "actions",
          sortable: false,
        },
      ];
    },
  },
  methods: {
    editItem(item) {
      this.selectedAnnotation = Object.assign({}, item);
      this.showEditDialog = true;
    },
    cancelEdit() {
      this.showEditDialog = false;
      this.selectedAnnotation = {};
      this.$refs.widget.clean();
    },
    cancelDelete() {
      this.showDeleteDialog = false;
      this.selectedAnnotation = {};
    },
    deleteItem(item) {
      this.selectedAnnotation = Object.assign({}, item);
      this.showDeleteDialog = true;
    },
    async deleteAnnotation() {
      if (this.selectedAnnotation.pk)
        await this.http({
          method: "delete",
          url: `/api/annotations/${this.selectedAnnotation.pk}`,
        });
      this.showDeleteDialog = false;
      this.$emit("updated");
    },
    annotationSaved() {
      this.showEditDialog = false;
      this.selectedAnnotation = {};
      this.$emit("updated");
      this.$refs.widget.clean();
    },
  },
  watch: {
    // Communicates back to the page the state such as sorting,
    // page and items per page to make the backend request.
    options: function () {
      this.$emit("update:options", this.options);
    },
  },
};
</script>

<style scoped>
.caption {
  font-size: 12px;
}
</style>
