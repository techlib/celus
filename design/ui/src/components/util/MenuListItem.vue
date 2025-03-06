<i18n lang="yaml" src="@/locales/notifications.yaml"></i18n>

<template>
  <!-- groups -->
  <v-list-group
    expand-icon="fas fa-caret-down"
    collapse-icon="fas fa-caret-up"
    v-if="item.items"
    v-model="expanded"
  >
    <template v-slot:activator="{ props }">
      <v-list-item v-bind="props" slim color="primary">
        <template #prepend>
          <v-icon class="fa-fw ml-2" size="x-small">{{ item.icon }}</v-icon>
        </template>
        <v-list-item-title class="d-flex align-center justify-space-between">
          {{ item.title }}
          <v-chip
            v-if="item.chip"
            :color="item.chip.color"
            size="x-small"
            class="float-right"
          >
            <v-icon v-if="item.chip.icon" size="x-small">{{
              item.chip.icon
            }}</v-icon>
            {{ item.chip.text }}
          </v-chip>
        </v-list-item-title>
      </v-list-item>
    </template>
    <MenuListItem
      v-for="subitem in visibleSubItems"
      :key="subitem.title"
      :item="subitem"
      :notifications="notifications"
      :level="level + 1"
      :chip="subitem.chip"
      @expand="expand"
    ></MenuListItem>
  </v-list-group>
  <!-- normal items -->
  <v-list-item
    v-else
    :to="{ name: item.linkTo }"
    ref="item"
    class="pl-4"
    rounded="0"
    slim
    :active="isActive(item)"
    :exact="false"
    color="primary"
    density="default"
    @change="change()"
  >
    <template #prepend v-if="item.icon">
      <v-icon class="fa-fw" size="x-small">{{ item.icon }}</v-icon>
    </template>
    <v-list-item-title class="d-flex align-center justify-space-between">
      {{ item.title }}
      <v-chip
        v-if="item.chip"
        :color="item.chip.color"
        variant="flat"
        size="x-small"
        class="float-right"
      >
        <v-icon v-if="item.chip.icon" size="small">{{ item.chip.icon }}</v-icon>
        {{ item.chip.title }}
      </v-chip>
      <v-tooltip
        location="bottom"
        v-if="item.linkTo in notifications"
        max-width="400"
      >
        <template v-slot:activator="{ props }">
          <v-icon
            v-bind="props"
            size="x-small"
            :color="notifications[item.linkTo].level"
            class="float-right"
          >
            fa
            {{
              notifications[item.linkTo].level === "warning"
                ? "fa fa-exclamation-triangle"
                : "fa fa-info-circle"
            }}
          </v-icon>
        </template>
        <span
          v-html="$t('notifications.' + notifications[item.linkTo].tooltip)"
        ></span>
      </v-tooltip>
    </v-list-item-title>
  </v-list-item>
</template>

<script>
import { useRoute } from "vue-router";
export default {
  name: "MenuListItem",

  emits: ["expand"],

  props: {
    item: { required: true, type: Object },
    notifications: { required: true, type: Object },
    level: { default: 0, type: Number },
    chip: { default: null, type: Object },
  },

  data() {
    return {
      expanded: null,
      route: useRoute(),
    };
  },

  computed: {
    visibleSubItems() {
      return this.item.items.filter((item) => item.show ?? true);
    },
  },

  methods: {
    change() {
      if (this.$refs.item.isActive) {
        this.$emit("expand");
      }
    },
    expand() {
      this.expanded = true;
    },

    isActive(item) {
      return this.route.path.startsWith(
        this.$router.resolve({ name: item.linkTo }).href,
      );
    },
  },
};
</script>

<style lang="scss">
.v-list-item__append {
  font-size: x-small;
}

.v-list-group__items {
  --indent-padding: 32px;
}
</style>
