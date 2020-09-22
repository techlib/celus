<i18n>
en:
    total: Total

cs:
    total: Celkem
</i18n>

<template>
  <v-data-table
    :headers="headers"
    :items="formattedRows"
    :footer-props="{ disableItemsPerPage: true, itemsPerPageOptions: [12] }"
    dense
  >
    <template #body.append="{ headers }">
      <tr class="totals">
        <th v-for="(total, i) in totals" :key="i" class="text-right">
          <span v-if="headers[i]['value'] !== primaryDimension">{{
            formatInteger(total)
          }}</span>
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
  },

  computed: {
    headers() {
      return this.columns.map((x) => {
        return { text: x, value: x, align: "right" };
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

<style scoped lang="scss">
tr.totals th {
  font-size: 0.875rem;
}
</style>
