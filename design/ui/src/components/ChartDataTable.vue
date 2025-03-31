<i18n lang="yaml">
en:
  total: Total

cs:
  total: Celkem
</i18n>

<template>
  <v-data-table
    :headers="headers"
    :items="formattedRows"
    :items-per-page="itemsPerPage"
    :items-per-page-options="[itemsPerPage]"
    class="chart-data-table"
  >
    <template #body.append="{ headers }">
      <tr class="totals">
        <th v-for="(total, i) in totals" :key="i" class="text-right">
          <span v-if="headers[0][i].value !== primaryDimension"
            >{{ formatInteger(total) }}
          </span>
          <span v-else>{{ $t("total") }}</span>
        </th>
      </tr>
    </template>
  </v-data-table>
</template>

<script>
import { formatInteger } from "../libs/numbers";

export default {
  name: "ChartDataTable",

  props: {
    columns: {
      required: true,
    },
    rows: {
      required: true,
    },
    primaryDimension: {},
    itemsPerPage: {
      default: 12,
      type: Number,
    },
  },

  computed: {
    headers() {
      return this.columns.map((x) => {
        return { title: x, value: x, align: "end", key: x };
      });
    },
    totals() {
      return this.columns.map((x) => {
        return this.rows
          .map((row) => (row[x] ? row[x] : 0))
          .reduce((x, y) => x + y);
      });
    },
    formattedRows() {
      return this.rows.map((x) => {
        let ret = {};
        for (let [key, value] of Object.entries(x)) {
          if (key != this.primaryDimension) {
            let int = formatInteger(value);
            if (int) ret[key] = int;
            else ret[key] = value;
          } else {
            ret[key] = value;
          }
        }
        return ret;
      });
    },
  },

  methods: {
    formatInteger,
  },
};
</script>

<style lang="scss">
tr.totals th {
  font-size: 0.875rem;
}

.chart-data-table {
  td {
    white-space: nowrap;
  }
}

.chart-data-table {
  .v-data-table__wrapper {
    width: 100%;
  }
}
.chart-data-table .v-data-table-footer .v-data-table-footer__items-per-page {
  display: none !important;
}

.chart-data-table .v-data-table-footer__info {
  margin-top: 14px;
  padding: 0 !important;
}
</style>
