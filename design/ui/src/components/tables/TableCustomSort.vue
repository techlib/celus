<template>
  <tr>
    <th
      v-for="column in columns"
      :key="column.key || column.value"
      @click="isColumnSortable(column) ? toggleSort(column) : null"
      :style="{
        cursor: isColumnSortable(column) ? 'pointer' : 'default',
      }"
      class="sortable-header"
    >
      <div
        v-if="column.value === selectColumnValue"
        class="d-flex align-center justify-flex-start"
      >
        <v-checkbox
          v-if="showSelectAll"
          :model-value="allSelected"
          @update:model-value="$emit('toggle-select-all', $event)"
          density="compact"
          hide-details
        />
      </div>
      <div
        v-else
        class="d-flex align-center header-content"
        :style="{ justifyContent: getJustifyContent(column.align) }"
      >
        <span
          :style="{
            opacity: isSorted(column) ? 1 : 0.7,
            fontWeight: isSorted(column) ? 'bold' : 'normal',
          }"
        >
          <!-- Check if parent data table has a slot for this column -->
          <template v-if="hasParentSlot(column)">
            <component :is="() => getParentSlot(column)" />
          </template>
          <!-- Fallback to the title of the column -->
          <span v-else>
            {{ column.title }}
          </span>
        </span>
        <v-icon
          v-if="isSorted(column)"
          class="ml-1"
          size="x-small"
          :icon="getSortIcon(column)"
        ></v-icon>
        <v-icon
          v-else-if="isColumnSortable(column)"
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
  emits: ["update:externalOrderBy", "toggle-select-all"],
  props: {
    columns: null,
    externalOrderBy: {
      type: Array,
      default: () => [],
    },
    showSelectAll: {
      type: Boolean,
      default: false,
    },
    allSelected: {
      type: Boolean,
      default: false,
    },
    unsortableColumnValues: {
      type: Array,
      default: () => [],
    },
    selectColumnValue: {
      type: String,
      default: "data-table-select",
    },
    parentData: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      orderBy: [],
    };
  },
  computed: {
    isColumnUnsortable() {
      return (column) => {
        return this.unsortableColumnValues.includes(column.value);
      };
    },
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
    isColumnSortable(column) {
      return (
        column.sortable !== false &&
        column.key &&
        !this.isColumnUnsortable(column)
      );
    },
    hasParentSlot(column) {
      const slotName = `header.${column.key || column.value}`;
      return (
        this.$parent && this.$parent.$slots && this.$parent.$slots[slotName]
      );
    },
    getParentSlot(column) {
      const slotName = `header.${column.key || column.value}`;
      if (
        this.$parent &&
        this.$parent.$slots &&
        this.$parent.$slots[slotName]
      ) {
        return this.$parent.$slots[slotName]({ column });
      }
      return null;
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
