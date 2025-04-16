<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/counter_registry.yaml"></i18n>

<template>
  <v-sheet :elevation="elevation" class="mb-2">
    <v-table density="compact" fixed-header>
      <thead>
        <tr>
          <th></th>
          <th>{{ $t("counter_registry.in_registry") }}</th>
          <th>{{ $t("counter_registry.in_celus") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr :class="diffClassRow(platformDiff, 'name')">
          <th>{{ $t("counter_registry.name") }}</th>
          <td :class="diffClassInRegistry(platformDiff, 'name')">
            {{ platformDiff.name }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'name')">
            {{ platformDiff.related_platform_name }}
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'short_name')">
          <th>{{ $t("counter_registry.short_name") }}</th>
          <td :class="diffClassInRegistry(platformDiff, 'short_name')">
            {{ platformDiff.short_name }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'short_name')">
            {{ platformDiff.related_platform_short_name }}
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'provider')">
          <th>{{ $t("counter_registry.provider") }}</th>
          <td :class="diffClassInRegistry(platformDiff, 'provider')">
            {{ platformDiff.provider }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'provider')">
            {{ platformDiff.related_platform_provider }}
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'url')">
          <th>{{ $t("counter_registry.url") }}</th>
          <td :class="diffClassInRegistry(platformDiff, 'url')">
            {{ platformDiff.url }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'url')">
            {{ platformDiff.related_platform_url }}
          </td>
        </tr>
        <CounterRegistryProviderLine
          v-for="provider in sushiProviders"
          :key="provider.counterVersion"
          :counter-version="provider.counterVersion"
          :in-registry="provider.inRegistry"
          :in-celus="provider.inCelus"
          :checked="checked"
        />
      </tbody>
    </v-table>
    <v-textarea
      variant="outlined"
      :label="$t('counter_registry.notes')"
      v-model="platformDiff.notes"
      :disabled="!editingNotes"
      rows="2"
      class="mx-2 mt-4"
    >
      <template #prepend>
        <v-btn
          style="pointer-events: auto; opacity: 1"
          variant="text"
          color="secondary"
          :icon="editingNotes ? 'fa fa-save' : 'fa fa-edit'"
          @click="toggleEdittingNotes"
          size="small"
          class="ml-2"
          :loading="savingNotes"
        ></v-btn>
      </template>
    </v-textarea>
  </v-sheet>
</template>

<script>
import CounterRegistryProviderLine from "./CounterRegistryProviderLine.vue";
import { counterVersionToStr } from "@/libs/sushi";
import cancellation from "@/mixins/cancellation";

export default {
  name: "CounterRegistryDiffWidget",
  components: {
    CounterRegistryProviderLine,
  },
  mixins: [cancellation],
  props: {
    platformDiff: {
      required: true,
      type: Object,
    },
    elevation: {
      default: 1,
      type: Number,
    },
    checked: {
      required: true,
      type: Boolean,
    },
  },

  data() {
    return {
      editingNotes: false,
      savingNotes: false,
    };
  },

  computed: {
    inCelusSushiProviders() {
      if (!this.platformDiff.related_platform_knowledgebase?.providers) {
        return [];
      }
      return this.platformDiff.related_platform_knowledgebase?.providers;
    },
    inRegistrySushiProviders() {
      if (!this.platformDiff.knowledgebase?.providers) {
        return [];
      }
      return this.platformDiff.knowledgebase.providers;
    },
    sushiProviders() {
      let result = {
        51: [null, null],
        5: [null, null],
        4: [null, null],
      };
      for (const provider of this.inRegistrySushiProviders) {
        result[provider.counter_version][0] = provider;
      }
      for (const provider of this.inCelusSushiProviders) {
        result[provider.counter_version][1] = provider;
      }
      return Object.entries(result)
        .filter((e) => e[1][0] || e[1][1])
        .map((e) => {
          let inRegistry = e[1][0] && {
            url: e[1][0].provider.url,
            reports: e[1][0].assigned_report_types.map((e) => e.report_type),
          };
          let inCelus = e[1][1] && {
            url: e[1][1].provider.url,
            reports: e[1][1].assigned_report_types.map((e) => e.report_type),
          };
          return {
            counterVersion: counterVersionToStr(parseInt(e[0])),
            inRegistry: inRegistry,
            inCelus: inCelus,
          };
        });
    },
  },

  methods: {
    diffClassInCelus(platformDiff, field) {
      let inRegistry = platformDiff[field];
      let inCelus = platformDiff[`related_platform_${field}`];
      if (inCelus == inRegistry && this.checked) {
        return "font-weight-bold";
      } else if (inCelus != inRegistry && !inRegistry && this.checked) {
        return "font-weight-bold";
      } else {
        return "";
      }
    },
    diffClassInRegistry(platformDiff, field) {
      if (!platformDiff[`keep_${field}`] && this.checked) {
        return "font-weight-bold";
      } else {
        return "";
      }
    },
    diffClassRow(platformDiff, field) {
      return platformDiff[`keep_${field}`] ? "" : "bg-red-lighten-5";
    },
    toggleEdittingNotes() {
      if (this.editingNotes) {
        this.triggerSaveNotes();
      } else {
        this.editingNotes = true;
      }
    },
    async triggerSaveNotes() {
      this.savingNotes = true;
      let result = await this.http({
        method: "patch",
        url: `/api/counter_registry/platforms_diff/${this.platformDiff.id}/`,
        data: { notes: this.platformDiff.notes },
      });
      if (!result.error) {
        this.editingNotes = false;
      }
      this.savingNotes = false;
    },
  },

  watch: {},

  mounted() {},
};
</script>

<style>
:deep(.v-input__prepend) {
  pointer-events: auto;
  opacity: 1;
}
</style>
