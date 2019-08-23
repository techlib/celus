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
                    v-model="searchDebounced"
                    append-icon="fa-search"
                    :label="$t('labels.search')"
                    single-line
                    hide-details
            ></v-text-field>
        </v-card-title>
        <v-data-table
                :items="titles"
                :headers="headers"
                :items-per-page.sync="itemsPerPage"
                :search="search"
                :loading="loading"
                :footer-props="{itemsPerPageOptions: [10, 25, 50, 100]}"
        >
            <template v-slot:item.name="props">
                <router-link v-if="platformId" :to="{name: 'platform-title-detail', params: {platformId: platformId, titleId: props.item.pk}}">{{ props.item.name }}</router-link>
                    <router-link v-else :to="{name: 'title-detail', params: {platformId: null, titleId: props.item.pk}}">{{ props.item.name }}</router-link>
            </template>
            <template v-slot:item.pub_type="props">
                <span :class="{'fa fa-book': props.item.pub_type==='B', 'far fa-copy': props.item.pub_type==='J'}"></span>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
  import axios from 'axios'
  import { mapActions } from 'vuex'
  import debounce from 'lodash/debounce'

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
        itemsPerPage: 25,
        loading: false,
        headers: [
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
            value: 'interest',
            align: 'end',
          },
        ]
      }
    },
    computed: {
      searchDebounced: {
        get () {
          return this.search
        },
        set: debounce(function (value) {
          this.search = value
        }, 500)
      }
    },
    methods: {
      ...mapActions({
        showSnackbar: 'showSnackbar',
      }),
      async loadData () {
        if (this.url) {
          this.loading = true
          try {
            let response = await axios.get(this.url)
            this.titles = response.data
          } catch (error) {
            this.showSnackbar({content: 'Error loading platforms: ' + error})
          } finally {
            this.loading = false
          }
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
