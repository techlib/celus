<i18n src="../locales/common.yaml"></i18n>

<template>
    <v-container>
        <v-row>
            <v-col>{{ $t('select_dates_text') }}</v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-menu
                        v-model="startDateMenu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        full-width
                        min-width="290px"
                >
                    <template v-slot:activator="{ on }">
                        <v-text-field
                                v-model="startDate"
                                :label="$t('title_fields.start_date')"
                                prepend-icon="fa-calendar"
                                readonly
                                v-on="on"
                        ></v-text-field>
                    </template>
                    <v-date-picker
                            v-model="startDate"
                            type="month"
                            no-title
                            :locale="$i18n.locale"
                    ></v-date-picker>
                </v-menu>
            </v-col>
            <v-col>
                <v-menu
                        v-model="endDateMenu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        full-width
                        min-width="290px"
                >
                    <template v-slot:activator="{ on }">
                        <v-text-field
                                v-model="startDate"
                                :label="$t('title_fields.end_date')"
                                prepend-icon="fa-calendar"
                                readonly
                                v-on="on"
                        ></v-text-field>
                    </template>
                    <v-date-picker
                            v-model="endDate"
                            type="month"
                            no-title
                            :locale="$i18n.locale"
                    ></v-date-picker>
                </v-menu>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-btn :disables="saving" @click="save()" v-text="$t('actions.save')"></v-btn>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
  import { mapActions, mapGetters, mapState } from 'vuex'
  import axios from 'axios'

  export default {
    name: 'AddAnnotationWidget',
    props: {
      platform: {required: false},
    },
    data () {
      return {
        startDate: null,
        endDate: null,
        annotation: null,
        endDateMenu: null,
        startDateMenu: null,
        saving: false,
      }
    },
    computed: {
      ...mapState({
        selectedOrganizationId: 'selectedOrganizationId',
      }),
      ...mapGetters({
        organizationSelected: 'organizationSelected',
      }),
      annotationData () {
        let data = {
          'start_date': this.startDate,
          'end_date': this.endDate,
        }
        if (this.organizationSelected) {
          data['organization_id'] = this.selectedOrganizationId
        }
        if (this.platform) {
          data['platform_id'] = this.platform
        }
        if (this.annotation) {
          data['pk'] = this.annotation.pk
        }
        return data
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      save () {
        if (this.annotation) {
          this.putData()
        } else {
          this.postData()
        }
      },
      async postData () {
        this.saving = true
        try {
          let response = await axios.post('/api/annotations/', this.annotationData)
          this.annotation = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error creating annotation: ' + error, color: 'error'})
        } finally {
          this.saving = false
        }
      },
      async putData () {
        this.saving = true
        try {
          let response = await axios.put(`/api/annotations/${this.annotation.pk}/`, this.annotationData)
          this.annotation = response.data
        } catch (error) {
          this.showSnackbar({content: 'Error saving annotation: ' + error, color: 'error'})
        } finally {
          this.saving = false
        }
      },
    },
  }
</script>

<style scoped lang="scss">
</style>
