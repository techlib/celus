<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<i18n lang="yaml">
en:
  title: Set last harvestable month
  desc: |
    If you know that data is not available before a certain date,
    you can set this date here. CELUS will use this information
    and not try to harvest data before this date.
  desc2_1: The date will be applied to all credentials you have currently selected.
  desc2_2: To unset a previously set date, just remove the date and hit apply.
  apply: Apply
  copy_tt: Copy date from previous entry
cs:
  title: Nastavete od kdy jsou data k dispozici
  desc: |
    Pokud víte, že data nejsou dostupná před určitým datem,
    můžete toto datum nastavit zde. CELUS bude tuto informaci používat a
    nebude se snažit stáhnout data před tímto datem.
  desc2_1: Datum bude použito na všechny přihlašovací údaje, které máte aktuálně vybrané.
  desc2_2: Chcete-li zrušit dříve nastavené datum, stačí odstranit hodnotu data a stisknout tlačítko Nastavit.
  apply: Nastavit
  copy_tt: Zkopírovat datum z předchozího záznamu
</i18n>

<template>
  <v-card>
    <v-card-title>{{ $t("title") }}</v-card-title>
    <v-card-text>
      <v-row>
        <v-col>
          <p>{{ $t("desc") }}</p>
          <p v-if="multipleCredentials">{{ $t("desc2_1") }}</p>
          <p>
            {{ $t("desc2_2") }}
          </p>
        </v-col>
      </v-row>
      <v-row class="mt-0">
        <v-col>
          <MonthEntry
            v-model="lastHarvestableMonth"
            :multiple-values="multipleValues"
            @update:modelValue="multipleValues = false"
          ></MonthEntry>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="pb-4">
      <v-spacer></v-spacer>
      <v-btn
        @click="closeDialog()"
        variant="flat"
        elevation="2"
        color="defaultButton"
        >{{ $t("close") }}</v-btn
      >
      <v-btn
        @click="trigger"
        variant="flat"
        elevation="2"
        color="primary"
        :loading="saving"
        :disabled="multipleValues"
      >
        {{ $t("apply") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";
import MonthEntry from "@/components/util/MonthEntry";

export default {
  name: "LastHarvestableMonthWidget",

  emits: ["apply", "close"],

  components: {
    MonthEntry,
  },

  mixins: [cancellation],

  props: {
    credentials: { required: true, type: Array },
    updateBackend: { required: false, type: Boolean, default: false },
  },

  data() {
    let currentValues = [
      ...new Set(this.credentials.map((e) => e?.last_harvestable_month)),
    ];
    let multipleValues = false;
    let lastHarvestableMonth = null;
    if (currentValues.length > 1) {
      multipleValues = true;
    } else {
      // only one value present => preset it
      lastHarvestableMonth = currentValues[0] || null;
    }
    return {
      saving: false,
      lastHarvestableMonth: lastHarvestableMonth,
      multipleValues: multipleValues,
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    closeDialog() {
      this.$emit("close");
    },
    applyDialog(result) {
      this.$emit("apply", {
        values: this.dataForTrigger,
        updated: result?.response?.data?.updated || 0,
      });
    },
    async trigger() {
      if (this.updateBackend) {
        this.saving = true;
        const result = await this.http({
          method: "post",
          url: this.triggerUrl,
          data: this.dataForTrigger,
        });
        if (!result.error) {
          this.applyDialog(result);
        }
        this.saving = false;
      } else {
        this.applyDialog(null);
      }
    },
  },

  computed: {
    triggerUrl() {
      return "/api/sushi-credentials/update-last-harvestable-month/";
    },
    dataForTrigger() {
      return this.credentials.map((cred) => {
        return {
          credentials_id: cred?.pk || null,
          last_harvestable_month: !this.lastHarvestableMonth
            ? null
            : `${this.lastHarvestableMonth}-01`,
        };
      });
    },
    multipleCredentials() {
      return this.credentials.length > 1;
    },
  },

  watch: {
    lastHarvestableMonth() {
      this.multipleValues = false;
    },
  },
};
</script>

<style lang="scss"></style>
