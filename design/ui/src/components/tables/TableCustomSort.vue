<template>
  <tr>
    <th
      v-for="column in columns"
      :key="column.key || column.value"
      @click="
        column.sortable !== false && column.key ? toggleSort(column) : null
      "
      :style="{
        cursor: column.sortable !== false && column.key ? 'pointer' : 'default',
      }"
      class="sortable-header"
    >
      <div
        class="d-flex align-center"
        :style="{ justifyContent: getJustifyContent(column.align) }"
      >
        {{ column.title }}
        <v-icon
          v-if="isSorted(column)"
          class="ml-1"
          size="x-small"
          :icon="getSortIcon(column)"
        ></v-icon>
        <v-icon
          v-else-if="column.sortable !== false && column.key"
          class="ml-1 ghost-arrow"
          size="x-small"
        >
          {{
            column.order === "reverse" ? "fas fa-sort-down" : "fas fa-sort-up"
          }}
        </v-icon>
      </div>
    </th>
  </tr>
</template>

<script>
export default {
  props: {
    columns: null,
    externalOrderBy: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      orderBy: [],
    };
  },
  watch: {
    externalOrderBy: {
      handler(newVal) {
        this.orderBy = newVal;
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    getJustifyContent(align) {
      if (!align) return "flex-start";
      const alignMap = {
        start: "flex-start",
        end: "flex-end",
        center: "center",
      };
      return alignMap[align] || "flex-start";
    },
    toggleSort(column) {
      // Ensure column has a key property
      if (!column.key) {
        console.warn("Column missing key property:", column);
        return;
      }

      const current = this.orderBy.find((item) => item.key === column.key);
      let nextSortBy = [];
      if (column?.order === "reverse") {
        if (!current) {
          nextSortBy = [{ key: column.key, order: "desc" }];
        } else if (current.order === "desc") {
          nextSortBy = [{ key: column.key, order: "asc" }];
        } else {
          nextSortBy = [];
        }
      } else {
        if (!current) {
          nextSortBy = [{ key: column.key, order: "asc" }];
        } else if (current.order === "asc") {
          nextSortBy = [{ key: column.key, order: "desc" }];
        } else {
          nextSortBy = [];
        }
      }
      this.orderBy = nextSortBy;
      this.$emit("update:externalOrderBy", this.orderBy);
    },
    isSorted(column) {
      if (!column.key) return false;
      return this.orderBy.some((item) => item.key === column.key);
    },
    getSortOrder(column) {
      if (!column.key) return null;
      const item = this.orderBy.find((s) => s.key === column.key);
      return item?.order || null;
    },
    getSortIcon(column) {
      const order = this.getSortOrder(column);
      if (order === "asc") return "fas fa-sort-up";
      if (order === "desc") return "fas fa-sort-down";
      return "";
    },
  },
};
</script>

<style scoped lang="scss">
.sortable-header {
  &:hover {
    .ghost-arrow {
      opacity: 0.4;
    }
  }
}
.ghost-arrow {
  opacity: 0;
  transition: opacity 0.2s ease;
}
</style>
