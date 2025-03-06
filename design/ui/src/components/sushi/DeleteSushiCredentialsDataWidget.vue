<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  delete: Delete
  heading: Delete SUSHI credentials
  platform_name: related to platform <strong>{name}</strong>
  credentials_title: <strong>{title}</strong>
  perex: |
    You are about to delete SUSHI credentials {title}. All the data downloaded by these credentials will be preserved.
  also_delete_data: Delete all the data downloaded by these SUSHI credentials as well.
  delete_all_platform_data: 'Note: In case you would like to delete all the data affiliated with the platform <i>{platform}</i>, you can do so in the "Platforms" section'
  link: here
  delete_warning: |
    This action cannot be undone. Data will be irreversibly lost.
  success: SUSHI credentials were successfully deleted.
  success_also_delete_data: SUSHI credentials were successfully deleted. Deleting of the data will be done in the background and may take up to a few hours.
  error: "Error deleting SUSHI credentials: {error}"
  cancel: Cancel
  close: Close

cs:
  delete: Smazat
  heading: Smazat přístupové údaje SUSHI
  platform_name: přidružené k platformě <strong>{name}</strong>
  credentials_title: <strong>{title}</strong>
  perex: |
    Chystáte se smazat přístupové údaje SUSHI {title}. Všechna data stažená těmito přístupovými údaji budou zachována.
  also_delete_data: Smazat také všechna data stažená těmito přístupovými údaji SUSHI.
  delete_all_platform_data: Pokud chcete smazat všechna data přidružená k platformě <i>{platform}</i>, můžete to udělat v sekci "Platformy"
  link: zde
  delete_warning: |
    Tato akce je nevratná. Data budou nenávratně ztracena.
  success: Přístupové údaje SUSHI byly úspěšně smazány.
  success_also_delete_data: Přístupové údaje SUSHI byly úspěšně smazány. Mazání dat stažených těmito přístupovými údaji bude probíhat na pozadí a může trvat i několik hodin.
  error: "Chyba při mazání přístupových údajů SUSHI: {error}"
  cancel: Zrušit
  close: Zavřít
</i18n>

<template>
  <span>
    <v-btn color="error" variant="flat" @click="dialog = true">
      <v-icon size="small" class="mr-1">fa fa-trash-alt</v-icon>
      {{ $t("delete") }}
    </v-btn>
    <v-dialog v-model="dialog" max-width="500px">
      <v-card>
        <v-card-title>{{ $t("heading") }}</v-card-title>
        <v-card-text>
          <p
            v-html="
              $t('perex', {
                title: credentials.title
                  ? $t('credentials_title', { title: credentials.title })
                  : $t('platform_name', { name: platform.name }),
              })
            "
            class="text-disabled text"
          ></p>
          <v-checkbox
            v-model="alsoDeleteData"
            :label="$t('also_delete_data')"
            :disabled="success || !!error || loading"
            color="primary"
            class="mt-6 checkbox_delete"
          ></v-checkbox>
          <p class="text-disabled text">
            <span
              v-html="
                $t('delete_all_platform_data', {
                  platform: platform.name,
                }) + ' '
              "
            ></span>
            <span>
              <router-link
                :to="{
                  name: 'platform-detail',
                  params: { platformId: platform.pk },
                  query: { tab: 'admin' },
                }"
                >{{ $t("link") }}</router-link
              >
            </span>
            <span>.</span>
          </p>
          <v-alert
            v-if="alsoDeleteData && !success && !error"
            type="warning"
            variant="outlined"
            class="mt-4"
          >
            <span v-html="$t('delete_warning')"></span>
          </v-alert>
          <v-alert v-if="success" type="success" variant="outlined">
            <span
              v-html="
                alsoDeleteData ? $t('success_also_delete_data') : $t('success')
              "
            ></span>
          </v-alert>
          <v-alert v-if="error" type="error" variant="outlined">
            <span v-html="$t('error', { error: error.message })"></span>
          </v-alert>
        </v-card-text>
        <v-card-actions class="pb-4 mx-2">
          <v-spacer></v-spacer>
          <v-btn
            v-if="!success && !error"
            color="error"
            variant="elevated"
            @click="performDelete"
            hide-detaile
            :loading="loading"
            :disabled="loading"
            >{{ $t("delete") }}</v-btn
          >
          <v-btn @click="closeDialog" variant="elevated" color="defaultButton">
            <v-icon v-if="success || error" size="small" class="mr-1"
              >fa fa-times</v-icon
            >
            {{ success || error ? $t("close") : $t("cancel") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>

<script>
import axios from "axios";

export default {
  name: "DeleteSushiCredentialsDataWidget",
  props: {
    credentials: {
      type: Object,
      required: true,
    },
    platform: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      dialog: false,
      loading: false,
      error: null,
      alsoDeleteData: false,
      success: false,
    };
  },
  methods: {
    async performDelete() {
      if (this.credentials) {
        try {
          this.loading = true;
          this.error = null;
          await axios.delete(
            `/api/sushi-credentials/${this.credentials.pk}/?delete_data=${this.alsoDeleteData}`,
          );

          this.success = true;
          this.loading = false;
        } catch (error) {
          this.error = error;
        } finally {
          this.loading = false;
        }
      }
    },
    closeDialog() {
      this.dialog = false;
      if (this.success) {
        this.$emit("deleted");
      }
    },
  },
};
</script>
<style scoped>
.text {
  font-size: 14px;
}

.checkbox_delete {
  margin-left: -12px;
}
</style>
