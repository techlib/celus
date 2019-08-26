<i18n src="../locales/common.yaml"></i18n>

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
                    v-for="item in group.items"
                    :key="item.title"
                    :to="{name: item.linkTo}"
            >
               <!-- exact - use this attr on v-list-tile to prevent matching / -->

                <v-list-item-action>
                    <v-icon>{{ item.icon }}</v-icon>
                </v-list-item-action>

                <v-list-item-content>
                    <v-list-item-title>{{ item.title }}</v-list-item-title>
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
        }),
        groups () {
          return [
          {
            title: this.$i18n.t('pages.content'),
            items: [
              { title: this.$i18n.t('pages.platforms'), icon: 'far fa-list-alt', linkTo: 'platform-list' },
              { title: this.$i18n.t('pages.all_titles'), icon: 'far fa-copy', linkTo: 'title-list' },
              ],
            show: true,
          },
            {
              title: this.$i18n.t('pages.admin'),
              items: [
                { title: this.$i18n.t('pages.sushi_management'), icon: 'far fa-arrow-alt-circle-down', linkTo: 'sushi-credentials-list', show: this.showAdminStuff },
                { title: this.$t('pages.sushi_fetch_attempts'), icon: 'fa-retweet', linkTo: 'sushi-fetch-attempts', show: this.showAdminStuff },
                { title: this.$t('pages.import_batches'), icon: 'fa-file-import', linkTo: 'import-batch-list', show: this.showAdminStuff },
              ],
              show: this.showAdminStuff,

            }
         ]
      },
      activeGroups () {
        return this.groups.filter(item => item.show)
      }
    }
  }
</script>
