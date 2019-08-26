<i18n>
en:
    dim:
        report: Report
        organization: Organization
        platform: Platform

cs:
    dim:
        report: Report
        organization: Organizace
        platform: Platforma
</i18n>

<template>
    <v-container>
        <v-row>
            <v-col>
        <v-select
                :items="xDimensions"
                v-model="x"
                label="X"
        ></v-select>
            </v-col>
            <v-col>
        <v-select
                :items="yDimensions"
                v-model="y"
                label="Y"
        ></v-select>
            </v-col>
        </v-row>
        <v-row>
            <v-simple-table dense>
                <thead>
                <tr>
                    <td></td>
                    <th v-for="col in columns" :key="col">{{ col }}</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(row, index) in rows" :key="row">
                    <th>{{ row }}</th>
                    <td v-for="(rec, index2) in tableData[index]"
                        :class="rec.total === 0 ? '' : rec.success === 0 ? 'bad' : rec.success === rec.total ? 'great': 'partial'" class="text-center">
                        {{ rec.total ? rec.success || '-' : ''}}
                        {{ rec.total ? '/' : '' }}
                        {{ rec.total ? rec.failure || '-' : ''}}
                    </td>
                </tr>
                </tbody>
            </v-simple-table>
        </v-row>

    </v-container>
</template>

<script>

  import axios from 'axios'
  import {mapActions} from 'vuex'

  export default {
    name: "SushiFetchAttemptsPage",
    data () {
      return {
        statsData: [],
        x: 'report',
        y: 'platform',
        dimensionsRaw: ['organization', 'report', 'platform'],
        columns: [],
        rows: [],
        tableData: {},
      }
    },
    computed: {
      statsUrl () {
        return `/api/sushi-fetch-attempt-stats/?x=${this.x}&y=${this.y}`
      },
      dimensions () {
        return this.dimensionsRaw.map(item => {return {value: item, text: this.$t('dim.'+item)}})
      },
      xDimensions () {
        return this.dimensions
      },
      yDimensions () {
        let x = this.x
        return this.dimensions.filter(item => item.value !== x)
      },
    },
    methods:{
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadAttemptStats () {
        try {
          let response = await axios.get(this.statsUrl)
          this.statsData = response.data
          this.dataToTable()
        } catch (error) {
          this.showSnackbar({content: 'Error fetching SUSHI attempt data: ' + error, color: 'error'})
        }
      },
      dataToTable () {
        let columns = new Set()
        let rows = new Set()
        for (let rec of this.statsData) {
          columns.add(rec[this.x])
          rows.add(rec[this.y])
        }
        this.columns = [...columns]
        this.columns.sort((a, b) => a.localeCompare(b))
        this.rows = [...rows]
        this.rows.sort((a, b) => a.localeCompare(b))
        // create an empty matrix
        let out = []
        for (let col in this.rows) {
          let rowRec = []
          for (let row in this.columns) {
            rowRec.push({total: 0})
          }
          out.push(rowRec)
        }
        // fill it
        for (let rec of this.statsData) {
          let x = this.columns.indexOf(rec[this.x])
          let y = this.rows.indexOf(rec[this.y])
          out[y][x] = {
            success: rec.success_count,
            failure: rec.failure_count,
            total: (rec.success_count || 0) + (rec.failure_count || 0)
          }
        }
        this.tableData = out
      }
    },
    watch: {
      statsUrl () {
        this.loadAttemptStats()
      },
    },
    mounted() {
      this.loadAttemptStats()
    }

  }
</script>

<style scoped lang="scss">

    td.bad {
        background-color: #eeb3b4;
    }
    td.partial {
        background-color: #f3e2ae;
    }
    td.great {
        background-color: #b7e2b1;
    }

</style>
