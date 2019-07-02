<i18n src="../locales/common.yaml"></i18n>

<template>
    <div class="org">
        <span class="sc">{{ $t('organization') }}</span>:
        <strong>{{ selectedOrganization !== null ? selectedOrganization.name : '-'}}</strong>
    </div>
</template>
<script>
  import { mapGetters } from 'vuex'

  export default {
    name: 'OrganizationSelector',
    computed: {
      ...mapGetters({
        selectedOrganization: 'selectedOrganization',
      })
    }
  }
</script>
<style lang="scss">

    div.org {
        display: inline-block;
        font-size: 1.25rem;
    }

    .sc {
        font-variant: small-caps;
    }

    .v-select.v-text-field.short input {
        max-width: 0;
    }

</style>
