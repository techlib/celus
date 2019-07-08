<i18n>
en:
    columns:
        id: ID
        name: Name
        type: Type
        isbn: ISBN
        issn: ISSN
        eissn: eISSN
        doi: DOI
cs:
    columns:
        id: ID
        name: Název
        type: Typ
        isbn: ISBN
        issn: ISSN
        eissn: eISSN
        doi: DOI
</i18n>


<template>
    <v-data-table
            :items="titles"
            :headers="headers"
            :pagination.sync="pagination"
    >
        <template v-slot:items="props">
            <td class="text-xs-right">{{ props.item.pk }}</td>
            <td>{{ props.item.name }}</td>
            <td>{{ props.item.pub_type }}</td>
            <td>{{ props.item.isbn }}</td>
            <td>{{ props.item.issn }}</td>
            <td>{{ props.item.eissn }}</td>
            <td>{{ props.item.doi }}</td>
        </template>
    </v-data-table>
</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'

  export default {
    name: 'TitleList',
    props: {
      url: {required: true},
    },
    data () {
      return {
        titles: [],
        pagination: {
          sortBy: 'name',
          rowsPerPage: 25,
        },
        headers: [
          {
            text: this.$i18n.t('columns.id'),
            value: 'pk'
          },
          {
            text: this.$i18n.t('columns.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('columns.type'),
            value: 'pub_type'
          },
          {
            text: this.$i18n.t('columns.isbn'),
            value: 'isbn'
          },
          {
            text: this.$i18n.t('columns.issn'),
            value: 'issn'
          },
          {
            text: this.$i18n.t('columns.eissn'),
            value: 'eissn'
          },
          {
            text: this.$i18n.t('columns.doi'),
            value: 'doi'
          },
        ]
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      loadData () {
        if (this.url) {
          axios.get(this.url)
            .then(response => {
              this.titles = response.data
            })
            .catch(error => {
              this.showSnackbar({content: 'Error loading platforms: ' + error})
            })
        }
      }
    },
    watch: {
      url () {
        this.loadData()
      }
    }
  }
</script>

<style scoped>

</style>
