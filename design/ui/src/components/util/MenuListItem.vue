<i18n lang="yaml" src="@/locales/notifications.yaml"></i18n>

<template>
  <!-- groups -->
  <v-list-group v-if="item.items">
    <template v-slot:activator>
      <v-list-item-icon>
        <v-icon class="fa-fw">{{ item.icon }}</v-icon>
      </v-list-item-icon>
      <v-list-item-content>
        <v-list-item-title>{{ item.title }}</v-list-item-title>
      </v-list-item-content>
    </template>
    <template #appendIcon>
      <v-icon small>fa fa-caret-down</v-icon>
    </template>
    <MenuListItem
      v-for="subitem in visibleSubItems"
      :key="subitem.title"
      :item="subitem"
      :notifications="notifications"
      :level="level + 1"
    />
  </v-list-group>

  <!-- normal items -->
  <v-list-item
    v-else
    :to="{ name: item.linkTo }"
    :class="`pl-${4 + 8 * level}`"
  >
    <v-list-item-icon v-if="level === 0">
      <v-icon class="fa-fw">{{ item.icon }}</v-icon>
    </v-list-item-icon>

    <v-list-item-content>
      <v-list-item-title>
        {{ item.title }}
        <v-tooltip bottom v-if="item.linkTo in notifications" max-width="400">
          <template v-slot:activator="{ on }">
            <v-icon
              v-on="on"
              x-small
              :color="notifications[item.linkTo].level"
              class="float-right"
            >
              fa
              {{
                notifications[item.linkTo].level === "warning"
                  ? "fa-exclamation-triangle"
                  : "fa-info-circle"
              }}
            </v-icon>
          </template>
          <span
            v-html="$t('notifications.' + notifications[item.linkTo].tooltip)"
          ></span>
        </v-tooltip>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
export default {
  name: "MenuListItem",

  props: {
    item: { required: true, type: Object },
    notifications: { required: true, type: Object },
    level: { default: 0, type: Number },
  },

  computed: {
    visibleSubItems() {
      return this.item.items.filter((item) => item.show ?? true);
    },
  },
};
</script>

<style>
/*
the following overrides the default vuetify setting of min-width of 48px for the icon, which
shortens the text before the icon unnecessarily
*/
.v-list-group
  .v-list-group__header
  .v-list-item__icon.v-list-group__header__append-icon {
  min-width: 0;
}
</style>
