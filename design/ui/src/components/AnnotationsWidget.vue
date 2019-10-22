<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-container v-if="annotations.length" fluid>
        <v-row>
            <v-col cols="auto">
                <h3 v-text="$t('labels.annotations')"></h3>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto" v-if="allowAdd">
                <v-btn @click="showAddDialog = true" small dark fab color="primary"><v-icon small>fa-plus</v-icon></v-btn>
            </v-col>
        </v-row>
        <div>
            <v-expansion-panels
                    v-model="panel"
                    multiple
                    accordion
            >
                <v-expansion-panel v-for="annot in annotations" :key="annot.pk">
                    <v-expansion-panel-header>
                        <span>
                            <v-icon v-if="annot.level === 'important'" color="warning" class="mr-3" small>fa-exclamation-triangle</v-icon>
                            <v-icon v-else color="info" class="mr-3" small>fa-info-circle</v-icon>
                            <span>{{ annot.subject }}</span>
                        </span>
                    </v-expansion-panel-header>
                    <v-expansion-panel-content>
                        <table class="overview">
                            <tr v-if="annot.platform">
                                <td v-text="$t('platform')+':'" class="pr-2"></td>
                                <th v-text="annot.platform.name"></th>
                            </tr>
                            <tr v-if="annot.organization">
                                <td v-text="$t('organization')+':'" class="pr-2"></td>
                                <th v-text="annot.organization.name"></th>
                            </tr>
                            <tr v-if="annot.start_date">
                                <td v-text="$t('title_fields.start_date')+':'" class="pr-2"></td>
                                <th v-text="annot.start_date"></th>
                            </tr>
                            <tr v-if="annot.end_date">
                                <td v-text="$t('title_fields.end_date')+':'" class="pr-2"></td>
                                <th v-text="annot.end_date"></th>
                            </tr>
                        </table>
                        <p v-if="annot.short_message" class="pt-2">
                            {{ annot.short_message }}
                        </p>
                        <p v-text="annot.message" v-if="annot.message"></p>
                    </v-expansion-panel-content>
                </v-expansion-panel>
            </v-expansion-panels>
        </div>
        <div v-if="allowAdd">
            <v-dialog
                    v-model="showAddDialog"
            >
                <v-card>
                    <v-card-title v-text="$t('add_annotation')"></v-card-title>
                    <v-card-text>
                        <AnnotationCreateModifyWidget
                                :platform="platform"
                                @saved="annotationSaved()"
                        />
                    </v-card-text>
                </v-card>
            </v-dialog>
        </div>
    </v-container>

</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'
  import AnnotationCreateModifyWidget from './AnnotationCreateModifyWidget'

  export default {
    name: 'AnnotationsWidget',
    components: {
      AnnotationCreateModifyWidget,
    },
    props: {
      platform: {required: false, type: Object},
      allowAdd: {required: false, default: false, type: Boolean},
    },
    data () {
      return {
        annotations: [],
        panel: [],
        showAddDialog: false,
      }
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        dateRangeStart: 'dateRangeStartText',
        dateRangeEnd: 'dateRangeEndText',
        organizationSelected: 'organizationSelected',
      }),
      annotationsUrl () {
        let url = `/api/annotations/?start_date=${this.dateRangeStart}&end_date=${this.dateRangeEnd}`
        if (this.organizationSelected) {
          url += `&organization=${this.selectedOrganizationId}`
        }
        if (this.platform) {
          url += `&platform=${this.platform.pk}`
        }
        return url
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async fetchAnnotations () {
        this.annotations = []
        try {
          let response = await axios.get(this.annotationsUrl)
          this.annotations = response.data
          this.$emit('loaded', {count: this.annotations.length})
        } catch (error) {
          this.showSnackbar({content: 'Error loading annotations: ' + error, color: 'error'})
        }
      },
      annotationSaved () {
        this.showAddDialog = false
        this.fetchAnnotations()
      }
    },
    mounted () {
      this.fetchAnnotations()
    },
    watch: {
      annotationsUrl () {
        this.fetchAnnotations()
      }
    }
  }
</script>

<style scoped lang="scss">

    table.overview {
        th {
            text-align: left;
        }
    }

</style>
