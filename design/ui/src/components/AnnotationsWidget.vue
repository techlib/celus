<i18n src="../locales/common.yaml"></i18n>

<template>
    <div v-if="annotations.length">
        <h3 v-text="$t('labels.annotations')"></h3>
        <div>
            <v-expansion-panels
                    v-model="panel"
                    multiple
                    accordion
            >
                <v-expansion-panel v-for="annot in annotations" :key="annot.pk">
                    <v-expansion-panel-header><strong>{{ annot.subject }}</strong></v-expansion-panel-header>
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
    </div>

</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'

  export default {
    name: 'AnnotationsWidget',
    props: {
      platform: {required: false},
    },
    data () {
      return {
        annotations: [],
        panel: [],
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
          url += `&platform=${this.platform}`
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
        } catch (error) {
          this.showSnackbar({content: 'Error loading annotations: ' + error, color: 'error'})
        }
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
