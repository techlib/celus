<i18n lang="yaml">
en:
  no_data_platform: There are no platforms to display. To add some, please
  no_data_title: There are no titles to display. To get some, please
  add_sushi: Add SUSHI credentials
  manual_upload: Alternatively you can {manual_upload_link} data for non-SUSHI platforms or archives.
  manually_upload: manually upload

cs:
  no_data_platform: Nejsou k dispozici žádné platformy k zobrazení. Pro jejich získání stačí
  no_data_title: Nejsou k dispozici žádné tituly k zobrazení. Pro jejich získání stačí
  add_sushi: Přidat SUSHI přístupové údaje
  manual_upload: Alternativně můžete {manual_upload_link} data pro platformy, které nepodporují SUSHI, nebo archivy.
  manually_upload: manuálně nahrát
</i18n>

<template>
  <div class="py-8">
    <p>{{ $t(`no_data_${scope}`) }}</p>

    <p class="text-center">
      <v-btn
        color="primary"
        :to="platformId ? null : { name: 'sushi-credentials-list' }"
        @click="platformId ? $emit('goto-sushi') : null"
        x-large
      >
        {{ $t("add_sushi") }}
      </v-btn>
    </p>

    <p>
      <i18n-t keypath="manual_upload" tag="span">
        <template #manual_upload_link>
          <router-link
            color="primary"
            :to="{ name: 'manual-data-upload-list' }"
            >{{ $t("manually_upload") }}</router-link
          >
        </template>
      </i18n-t>
    </p>
  </div>
</template>

<script>
export default {
  name: "NoDataInTableWidget",

  props: {
    scope: {
      required: true,
      type: String,
      validator: (value) => ["platform", "title"].includes(value),
    },
    platformId: {
      // when given, the button will link to the platform detail / SUSHI tab
      type: Number,
      default: null,
    },
  },
};
</script>

<style scoped lang="scss"></style>
