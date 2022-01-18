<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>
<i18n lang="yaml">
en:
  columns:
    subject: Title
    short_message: Message
    start_date: "@:title_fields.start_date"
    end_date: "@:title_fields.end_date"
    organization: "@:organization"
    platform: "@:platform"
    level: Level
    created: Created
    author: Author
    actions: Actions
  dates: Dates
  are_you_sure: "Are you sure to delete {0}?"
  info: Info
  important: Important

cs:
  columns:
    subject: Titulek
    short_message: Zpráva
    start_date: "@:title_fields.start_date"
    end_date: "@:title_fields.end_date"
    organization: "@:organization"
    platform: Platforma
    level: Typ
    created: Vytvořeno
    author: Autor
    actions: Akce
  dates: Data
  are_you_sure: "Určitě chcete smazat {0}?"
  info: Info
  important: Důležité
</i18n>

<template>
  <v-row>
    <v-col>
      <v-data-table
        :items="annotations"
        :headers="headers"
        sort-by="pk"
        :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
        :options.sync="options"
        :loading="loading"
        :page="page"
        :items-per-page="10"
        :server-items-length="serverItemsLength"
      >
        <template v-slot:top>
          <v-dialog
            v-model="showEditDialog"
            max-width="1240px"
            @click:outside="cancelEdit"
          >
            <v-card>
              <v-card-title v-text="$t('actions.edit')"></v-card-title>
              <v-card-text>
                <AnnotationCreateModifyWidget
                  ref="widget"
                  :annotation="selectedAnnotation"
                  :showDeleteButton="false"
                  @saved="annotationSaved"
                  @cancel="cancelEdit"
                />
              </v-card-text>
            </v-card>
          </v-dialog>
          <v-dialog v-model="showDeleteDialog" max-width="620px">
            <v-card>
              <v-card-title v-text="$t('actions.delete')"></v-card-title>
              <v-card-text>
                <i18n path="are_you_sure" tag="p">
                  <span class="font-weight-bold"
                    >{{ selectedAnnotation[`subject_${lang}`] }}
                  </span>
                </i18n>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn @click="cancelDelete()">{{ $t("cancel") }}</v-btn>
                <v-btn @click="deleteAnnotation()" color="error">
                  <v-icon small class="mr-2">fa-trash</v-icon>
                  {{ $t("actions.delete") }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </template>

        <template v-slot:[`item.level`]="{ item }">
          <v-tooltip bottom v-if="item.level == 'info'">
            <template v-slot:activator="{ on }">
              <v-icon small class="mr-2" color="blue" v-on="on">
                fas fa-info-circle
              </v-icon>
            </template>
            <i18n path="info" />
          </v-tooltip>
          <v-tooltip bottom v-if="item.level == 'important'">
            <template v-slot:activator="{ on }">
              <v-icon small class="mr-2" color="orange" v-on="on">
                fas fa-exclamation-triangle
              </v-icon>
            </template>
            <i18n path="important" />
          </v-tooltip>
        </template>

        <template v-slot:[`item.actions`]="{ item }">
          <v-icon
            v-if="item.can_edit"
            small
            class="mr-2"
            @click="editItem(item)"
          >
            fas fa-pen
          </v-icon>
          <v-icon
            v-if="item.can_edit"
            small
            class="mr-2"
            @click="deleteItem(item)"
          >
            fas fa-trash-alt
          </v-icon>
        </template>
      </v-data-table>
    </v-col>
  </v-row>
</template>

<script>
import AnnotationCreateModifyWidget from "./AnnotationCreateModifyWidget.vue";
import cancellation from "@/mixins/cancellation";

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
    };
  },

  computed: {
    organization() {
      return this.$store.state.selectedOrganizationId;
    },
    lang() {
      return this.$store.state.appLanguage || "en";
    },
    headers() {
      return [
        {
          text: this.$i18n.t("columns.subject"),
          value: `subject_${this.lang}`,
        },
        {
          text: this.$i18n.t("columns.organization"),
          value: `organization.name_${this.lang}`,
        },
        {
          text: this.$i18n.t("columns.platform"),
          value: "platform.name",
        },
        {
          text: this.$i18n.t("columns.level"),
          value: "level",
        },
        {
          text: this.$i18n.t("columns.author"),
          value: "author",
        },
        {
          text: this.$i18n.t("columns.actions"),
          value: "actions",
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
