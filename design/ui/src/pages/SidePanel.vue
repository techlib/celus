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
                <v-list-tile avatar>
                    <v-list-tile-action>
                        <v-icon>fa-th</v-icon>
                    </v-list-tile-action>

                    <v-list-tile-content>
                        {{ $t('menu') }}
                    </v-list-tile-content>

                    <v-list-tile-action>
                        <v-btn
                                icon
                                @click.stop="mini = !mini"
                        >
                            <v-icon>fa-chevron-left</v-icon>
                        </v-btn>
                    </v-list-tile-action>
                </v-list-tile>
            </v-list>
        </v-toolbar>

        <v-list class="pt-0" dense v-for="(group, index) in groups" :key="index" subheader>
            <v-subheader>{{ group.title }}</v-subheader>

            <v-list-tile
                    v-for="item in group.items"
                    :key="item.title"
                    :to="{name: item.linkTo}"
            >
               <!-- exact - use this attr on v-list-tile to prevent matching / -->

                <v-list-tile-action>
                    <v-icon>{{ item.icon }}</v-icon>
                </v-list-tile-action>

                <v-list-tile-content>
                    <v-list-tile-title>{{ item.title }}</v-list-tile-title>
                </v-list-tile-content>
            </v-list-tile>
        </v-list>
    </v-navigation-drawer>
</template>
<script>
  export default {
    name: 'SidePanel',
    data () {
      return {
        mini: false,
        drawer: true,
      }
    },
    computed: {
        groups () {
          return [
          {
            title: this.$i18n.t('pages.content'),
            items: [
              { title: this.$i18n.t('pages.platforms'), icon: 'far fa-list-alt', linkTo: 'platform-list' },
              { title: this.$i18n.t('pages.all_titles'), icon: 'far fa-copy', linkTo: 'title-list' },
              ]
          },
            {
              title: this.$i18n.t('pages.admin'),
              items: [
                { title: this.$i18n.t('pages.sushi_management'), icon: 'far fa-arrow-alt-circle-down', linkTo: 'sushi-credentials-list' },

              ]

            }
         ]
      }
    }
  }
</script>
