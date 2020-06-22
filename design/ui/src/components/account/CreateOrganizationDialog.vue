<i18n lang="yaml">
en:
    create_organization: Create your organization
    info_text: Your account is not associated with any organization yet. In order to use Celus
      we need to register your organization. Please fill in the following form.
    do_create: Create organization
    name: Name
    url: URL

cs:
    create_organization: Vytvořte svou organizaci
</i18n>

<template>
    <v-dialog v-model="showCreateOrganizationDialog" persistent max-width="600">
        <v-card>
            <v-card-title class="headline">{{ $t('create_organization') }}</v-card-title>
            <v-card-text>
                <div>{{ $t('info_text') }}</div>
                <v-divider class="my-3"></v-divider>

                <v-form :value="valid">
                    <v-text-field v-model="name" :label="$t('name') + '*'" aria-required="true"></v-text-field>
                    <v-text-field v-model="url" :label="$t('url')"></v-text-field>

                </v-form>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        @click="createOrganization"
                        :disabled="!valid"
                        class="ma-4"
                >{{ $t('do_create') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
  import { mapGetters } from 'vuex'

  export default {
    name: 'CreateOrganizationDialog',

    data () {
      return {
        name: '',
        url: '',
      }
    },

    computed: {
      ...mapGetters({
        showCreateOrganizationDialog: 'showCreateOrganizationDialog',
      }),
      valid () {
        return (this.name !== '')
      }
    },

    methods: {
      createOrganization () {
        console.log('creating')
      }
    }
  }
</script>

<style scoped>

</style>
