<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/notifications.yaml"></i18n>

<template>
    <v-navigation-drawer
            v-model="drawer"
            :mini-variant.sync="mini"
            clipped
            app
            mobile-break-point="900"
    >
        <v-toolbar flat class="transparent">
            <v-list class="pa-0">
                <v-list-item>
                    <v-list-item-action>
                        <v-icon>fa-th</v-icon>
                    </v-list-item-action>

                    <v-list-item-content>
                        {{ $t('menu') }}
                    </v-list-item-content>

                    <v-list-item-action>
                        <v-btn
                                icon
                                @click.stop="mini = !mini"
                        >
                            <v-icon>fa-chevron-left</v-icon>
                        </v-btn>
                    </v-list-item-action>
                </v-list-item>
            </v-list>
        </v-toolbar>

        <v-list class="pt-0" dense v-for="(group, index) in activeGroups" :key="index" subheader>
            <v-subheader>{{ group.title }}</v-subheader>

            <v-list-item
                    v-for="item in group.items.filter(item => item.show == null ? true : item.show)"
                    :key="item.title"
                    :to="{name: item.linkTo}"
            >
               <!-- exact - use this attr on v-list-tile to prevent matching / -->

                <v-list-item-action>
                    <v-icon class="fa-fw">{{ item.icon }}</v-icon>
                </v-list-item-action>

                <v-list-item-content>
                    <v-list-item-title>
                        {{ item.title }}
                        <v-tooltip bottom v-if="item.linkTo in notifications">
                            <template v-slot:activator="{on}">
                                <v-icon
                                        v-on="on"
                                        x-small
                                        :color="notifications[item.linkTo].level"
                                        class="float-right"
                                >
                                    fa
                                    {{ notifications[item.linkTo].level === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle' }}
                                </v-icon>
                            </template>
                            <span v-text="$t('notifications.'+notifications[item.linkTo].tooltip)"></span>
                        </v-tooltip>
                    </v-list-item-title>
                </v-list-item-content>
            </v-list-item>
        </v-list>
    </v-navigation-drawer>
</template>
<script>
  import { mapGetters, mapState } from 'vuex'

  export default {
    name: 'SidePanel',
    data () {
      return {
        mini: false,
        drawer: true,
      }
    },
    computed: {
        ...mapState({
          user: 'user',
        }),
        ...mapGetters({
          organization: 'selectedOrganization',
          showAdminStuff: 'showAdminStuff',
          showManagementStuff: 'showManagementStuff',
          notifications: 'getNotifications',
        }),
        groups () {
          return [
          {
            title: this.$i18n.t('pages.content'),
            items: [
              { title: this.$i18n.t('pages.dashboard'), icon: 'fas fa-tachometer-alt', linkTo: 'dashboard' },
              { title: this.$i18n.t('pages.platforms'), icon: 'far fa-list-alt', linkTo: 'platform-list' },
              { title: this.$i18n.t('pages.all_titles'), icon: 'far fa-copy', linkTo: 'title-list' },
              { title: this.$i18n.t('pages.heatmap'), icon: 'far fa-map', linkTo: 'heatmap' },
              ],
            show: true,
          },
            {
              title: this.$i18n.t('pages.admin'),
              items: [
                { title: this.$i18n.t('pages.management'), icon: 'fas fa-tools', linkTo: 'management', show: this.showManagementStuff },
                { title: this.$t('pages.maintenance'), icon: 'fa fa-toolbox', linkTo: 'maintenance', show: this.showManagementStuff },
                { title: this.$i18n.t('pages.sushi_management'), icon: 'far fa-arrow-alt-circle-down', linkTo: 'sushi-credentials-list', show: this.showAdminStuff },
                { title: this.$t('pages.sushi_fetch_attempts'), icon: 'fa-retweet', linkTo: 'sushi-fetch-attempts', show: this.showAdminStuff },
                { title: this.$t('pages.manual_data_uploads'), icon: 'fa-upload', linkTo: 'manual-data-upload-list', show: this.showAdminStuff },
                //{ title: this.$t('pages.import_batches'), icon: 'fa-file-import', linkTo: 'import-batch-list', show: this.showAdminStuff },
              ],
              show: this.showAdminStuff,

            }
         ]
      },
      activeGroups () {
        return this.groups.filter(group => group.show)
      }
    }
  }
</script>
