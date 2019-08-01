<i18n src="../locales/common.yaml"></i18n>
<i18n>
en:
    columns:
        interest: Interest
cs:
    columns:
        interest: Zájem
</i18n>


<template>
    <v-card>
        <v-card-title>
            <v-spacer></v-spacer>
            <v-text-field
                    v-model="search"
                    append-icon="fa-search"
                    :label="$t('labels.search')"
                    single-line
                    hide-details
            ></v-text-field>
        </v-card-title>
        <v-data-table
                :items="titles"
                :headers="headers"
                :pagination.sync="pagination"
                :search="search"
        >
            <template v-slot:items="props">
                <td class="text-xs-right">{{ props.item.pk }}</td>
                <td>
                    <router-link v-if="platformId" :to="{name: 'platform-title-detail', params: {platformId: platformId, titleId: props.item.pk}}">{{ props.item.name }}</router-link>
                    <router-link v-else :to="{name: 'title-detail', params: {platformId: null, titleId: props.item.pk}}">{{ props.item.name }}</router-link>
                </td>
                <td><span :class="{'fa fa-book': props.item.pub_type==='B', 'far fa-copy': props.item.pub_type==='J'}"></span></td>
                <td>{{ props.item.isbn }}</td>
                <td>{{ props.item.issn }}</td>
                <td>{{ props.item.eissn }}</td>
                <td>{{ props.item.doi }}</td>
                <td class="text-xs-right">{{ props.item.count }}</td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'

  export default {
    name: 'TitleList',
    props: {
      url: {required: true},
      platformId: {required: false}
    },
    data () {
      return {
        titles: [],
        search: '',
        pagination: {
          sortBy: 'name',
          rowsPerPage: 25,
        },
        headers: [
          {
            text: this.$i18n.t('title_fields.id'),
            value: 'pk'
          },
          {
            text: this.$i18n.t('title_fields.name'),
            value: 'name'
          },
          {
            text: this.$i18n.t('title_fields.type'),
            value: 'pub_type'
          },
          {
            text: this.$i18n.t('title_fields.isbn'),
            value: 'isbn'
          },
          {
            text: this.$i18n.t('title_fields.issn'),
            value: 'issn'
          },
          {
            text: this.$i18n.t('title_fields.eissn'),
            value: 'eissn'
          },
          {
            text: this.$i18n.t('title_fields.doi'),
            value: 'doi'
          },
          {
            text: this.$i18n.t('columns.interest'),
            value: 'count'
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
    },
    mounted() {
      this.loadData()
    }
  }
</script>

<style scoped>

</style>
