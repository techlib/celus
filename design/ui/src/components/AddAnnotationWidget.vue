<i18n src="../locales/common.yaml"></i18n>
<i18n src="../locales/dialog.yaml"></i18n>
<i18n>
en:
    labels:
        short_message: Annotation preamble
        message: Annotation text
        subject: Title
    level: Importance
    level_info: Info
    level_important: Important

cs:
    labels:
        short_message: Krátký úvod zprávy
        message: Text zprávy
        subject: Titulek
    level: Důležitost
    level_info: Informační
    level_important: Důležité
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
                <v-text-field
                        disabled
                        :value="selectedOrganization ? selectedOrganization.name : ''"
                        :label="$t('organization')"
                >
                </v-text-field>
            </v-col>
            <v-col v-if="platform">
                <v-text-field
                        disabled
                        :value="platform.name"
                        :label="$t('platform')"
                >
                </v-text-field>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="auto">
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
            <v-col cols="auto">
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
                                v-model="endDate"
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
            <v-spacer></v-spacer>
            <v-col cols="auto">
                <v-select
                        :items="importanceLevels"
                        :label="$t('level')"
                        v-model="level"
                >
                    <template v-slot:item="{item}">
                        <v-icon small class="mr-2" :color="item.color">{{ item.icon }}</v-icon>
                        {{ item.text }}
                    </template>
                    <template v-slot:selection="{item}">
                        <v-icon small class="mr-2" :color="item.color">{{ item.icon }}</v-icon>
                        {{ item.text }}
                    </template>
                </v-select>

            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12" md="6">
                <v-text-field
                        v-model="subjectCs"
                        :label="$t('labels.subject') + ' (' + $t('in_czech') + ') *'"
                        :rules="[required]"
                        maxlength="200"
                        counter
                >
                </v-text-field>
            </v-col>
            <v-col cols="12" md="6">
                <v-text-field
                        v-model="subjectEn"
                        :label="$t('labels.subject') + ' (' + $t('in_english') + ') *'"
                        :rules="[required]"
                        maxlength="200"
                        counter
                >
                </v-text-field>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12" md="6">
                <v-textarea
                        v-model="shortMessageCs"
                        :label="$t('labels.short_message') + ' (' + $t('in_czech') + ')'"
                        rows="2"
                        outlined
                        auto-grow
                >
                </v-textarea>
            </v-col>
            <v-col cols="12" md="6">
                <v-textarea
                        v-model="shortMessageEn"
                        :label="$t('labels.short_message') + ' (' + $t('in_english') + ')'"
                        rows="2"
                        outlined
                        auto-grow
                >
                </v-textarea>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12" md="6">
                <v-textarea
                        v-model="messageCs"
                        :label="$t('labels.message') + ' (' + $t('in_czech') + ')'"
                        rows="4"
                        outlined
                        auto-grow
                >
                </v-textarea>
            </v-col>
            <v-col cols="12" md="6">
                <v-textarea
                        v-model="messageEn"
                        :label="$t('labels.message') + ' (' + $t('in_english') + ')'"
                        rows="4"
                        outlined
                        auto-grow
                >
                </v-textarea>
            </v-col>
        </v-row>
        <v-row>
            <v-spacer></v-spacer>
            <v-col cols="auto">
                <v-btn :disables="saving" @click="save()" v-text="$t('save')"></v-btn>
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
      platform: {required: false, type: Object},
    },
    data () {
      return {
        startDate: null,
        endDate: null,
        annotation: null,
        subjectCs: '',
        subjectEn: '',
        shortMessageCs: '',
        shortMessageEn: '',
        messageCs: '',
        messageEn: '',
        level: 'info',
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
        selectedOrganization: 'selectedOrganization',
      }),
      importanceLevels () {
        return [
          {
            value: 'info',
            text: this.$t('level_info'),
            icon: 'fa-info-circle',
            color: 'info'
          },
          {
            value: 'important',
            text: this.$t('level_important'),
            icon: 'fa-exclamation-triangle',
            color: 'warning'
          },
        ]
      },
      annotationData () {
        let data = {
          'start_date': this.startDate ? this.startDate + '-01' : this.startDate,
          'end_date': this.endDate ? this.endDate + '-01' : this.endDate,
          'subject_cs': this.subjectCs,
          'subject_en': this.subjectEn,
          'short_message_cs': this.shortMessageCs,
          'short_message_en': this.shortMessageEn,
          'message_en': this.messageEn,
          'message_cs': this.messageCs,
          'level': this.level,
        }
        if (this.organizationSelected) {
          data['organization_id'] = this.selectedOrganizationId
        }
        if (this.platform) {
          data['platform_id'] = this.platform.pk
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
      required (v) {
        return !!v || this.$t('value_required')
      },
    },

  }
</script>

<style scoped lang="scss">
</style>
