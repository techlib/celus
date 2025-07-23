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
          <td v-if="unlinked">
            <strong v-if="selectedMissing">{{ newCelusPlatformName }}</strong>
          </td>
          <td v-else :class="diffClassInRegistry(platformDiff, 'name')">
            {{ platformDiff.name }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'name')">
            <strong v-if="selectedUnlinked">{{
              newRegistryPlatformName
            }}</strong>
            <span v-else>{{ platformDiff.related_platform_name }}</span>
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'short_name')">
          <th>{{ $t("counter_registry.short_name") }}</th>
          <td v-if="unlinked">
            <strong v-if="selectedMissing">{{
              newCelusPlatformShortName
            }}</strong>
          </td>
          <td v-else :class="diffClassInRegistry(platformDiff, 'short_name')">
            {{ platformDiff.short_name }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'short_name')">
            <strong v-if="selectedUnlinked">{{
              newRegistryPlatformShortName
            }}</strong>
            <span v-else>{{ platformDiff.related_platform_short_name }}</span>
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'provider')">
          <th>{{ $t("counter_registry.provider") }}</th>
          <td v-if="unlinked">
            <strong v-if="selectedMissing">{{
              newCelusPlatformProvider
            }}</strong>
          </td>
          <td v-else :class="diffClassInRegistry(platformDiff, 'provider')">
            {{ platformDiff.provider }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'provider')">
            <strong v-if="selectedUnlinked">{{
              newRegistryPlatformProvider
            }}</strong>
            <span v-else>{{ platformDiff.related_platform_provider }}</span>
          </td>
        </tr>
        <tr :class="diffClassRow(platformDiff, 'url')">
          <th>{{ $t("counter_registry.url") }}</th>
          <td v-if="unlinked">
            <strong v-if="selectedMissing">{{ newCelusPlatformURL }}</strong>
          </td>
          <td v-else :class="diffClassInRegistry(platformDiff, 'url')">
            {{ platformDiff.url }}
          </td>
          <td :class="diffClassInCelus(platformDiff, 'url')">
            <strong v-if="selectedUnlinked">{{
              newRegistryPlatformURL
            }}</strong>
            <span v-else>{{ platformDiff.related_platform_url }}</span>
          </td>
        </tr>
        <CounterRegistryProviderLine
          v-for="provider in sushiProviders"
          :key="provider.counterVersion"
          :counter-version="provider.counterVersion"
          :in-registry="provider.inRegistry || {}"
          :in-celus="provider.inCelus || {}"
          :checked="checked"
          :unlinked="unlinked"
        />
      </tbody>
    </v-table>
    <v-container>
      <v-row v-if="missing">
        <v-col>
          <v-autocomplete
            :items="unlinkedPlatforms"
            v-model="selectedUnlinked"
            item-title="name"
            item-value="id"
            density="compact"
            :custom-filter="platformsSearchFilter"
            return-object
            variant="outlined"
            hide-details
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props" title="">
                <div class="d-flex flex-column justify-lg-start">
                  <ItemBadge :item="item.raw" tag="span"></ItemBadge>
                  <span class="subtitle">
                    {{ item.raw.short_name }}
                  </span>
                </div>
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col cols="6" md="4" lg="3" xl="2">
          <v-btn
            color="secondary"
            :loading="linking"
            :disabled="!selectedUnlinked"
            @click="linkSelected"
          >
            {{ $t("counter_registry.link_local") }}
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="unlinked">
        <v-col>
          <v-autocomplete
            :items="missingPlatforms"
            v-model="selectedMissing"
            item-title="name"
            item-value="id"
            density="compact"
            :custom-filter="platformsSearchFilter"
            return-object
            variant="outlined"
            hide-details
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props" title="">
                <div class="d-flex flex-column justify-lg-start">
                  <ItemBadge :item="item.raw" tag="span"></ItemBadge>
                  <span class="subtitle">
                    {{ item.raw.short_name }}
                  </span>
                </div>
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col cols="6" md="4" lg="3" xl="2">
          <v-btn
            color="secondary"
            :loading="linking"
            :disabled="!selectedMissing"
            @click="linkSelected"
          >
            {{ $t("counter_registry.link_registry") }}
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col>
          <v-textarea
            variant="outlined"
            :label="$t('counter_registry.notes')"
            v-model="platformDiff.notes"
            :disabled="!editingNotes"
            rows="2"
          >
          </v-textarea>
        </v-col>
        <v-col cols="6" md="4" lg="3" xl="2">
          <v-btn
            color="secondary"
            @click="toggleEdittingNotes"
            :loading="savingNotes"
          >
            {{ $t("counter_registry.save_notes") }}
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-sheet>
</template>

<script>
import ItemBadge from "@/components/util/ItemBadge";
import CounterRegistryProviderLine from "./CounterRegistryProviderLine.vue";
import { counterVersionToStr } from "@/libs/sushi";
import cancellation from "@/mixins/cancellation";

export default {
  name: "CounterRegistryDiffWidget",
  components: {
    CounterRegistryProviderLine,
    ItemBadge,
  },
  emits: ["linked"],
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
    unlinkedPlatforms: {
      default: [],
      type: Array,
    },
    missingPlatforms: {
      default: [],
      type: Array,
    },
    missing: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      editingNotes: false,
      savingNotes: false,
      linking: false,
      selectedUnlinked: null,
      selectedMissing: null,
      unlinkedSaved: false,
      newRegistryPlatform: null,
      newRegistryPlatformName: null,
      newRegistryPlatformShortName: null,
      newRegistryPlatformProvider: null,
      newRegistryPlatformKnowledgebase: null,
      newRegistryPlatformURL: null,
      newCelusPlatform: null,
      newCelusPlatformName: null,
      newCelusPlatformShortName: null,
      newCelusPlatformProvider: null,
      newCelusPlatformKnowledgebase: null,
      newCelusPlatformURL: null,
    };
  },

  computed: {
    inCelusSushiProviders() {
      if (!this.platformDiff.related_platform_knowledgebase?.providers) {
        return [];
      }
      return this.platformDiff.related_platform_knowledgebase?.providers || [];
    },
    inRegistrySushiProviders() {
      if (!this.platformDiff.knowledgebase?.providers) {
        return [];
      }
      return this.platformDiff.knowledgebase.providers || [];
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
    unlinked() {
      return this.platformDiff.unlinked || false;
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
      if (this.unlinked) {
        return "";
      }
      if (!platformDiff[`keep_${field}`] && this.checked) {
        return "font-weight-bold";
      } else {
        return "";
      }
    },
    diffClassRow(platformDiff, field) {
      if (this.unlinked) {
        return "";
      }
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
    platformsSearchFilter(itemTitle, queryText, item) {
      const text = item.raw.name.toLowerCase();
      const shortName = item.raw.short_name.toLowerCase();
      const query = queryText.toLowerCase();
      return text.includes(query) || shortName.includes(query);
    },
    async linkSelected() {
      let registryId = null;
      let celusId = null;
      if (this.selectedMissing) {
        registryId = this.selectedMissing.id;
        celusId = this.platformDiff.id;
      } else if (this.selectedUnlinked) {
        registryId = this.platformDiff.id;
        celusId = this.selectedUnlinked.id;
      } else {
        // nothing selected
        return;
      }
      this.linking = true;
      let result = await this.http({
        method: "post",
        url: `/api/counter_registry/platforms_diff/${registryId}/link/`,
        data: { platform_id: celusId },
      });
      if (!result.error) {
        this.$emit("linked");
      }
      this.linking = false;
    },
  },

  watch: {
    selectedUnlinked(new_value) {
      this.newRegistryPlatform = new_value;
      this.newRegistryPlatformName = new_value?.name;
      this.newRegistryPlatformShortName = new_value?.short_name;
      this.newRegistryPlatformProvider = new_value?.provider;
      this.newRegistryPlatformKnowledgebase = new_value?.knowledgebase;
      this.newRegistryPlatformURL = new_value?.url;
    },
    selectedMissing(new_value) {
      this.newCelusPlatform = new_value;
      this.newCelusPlatformName = new_value?.name;
      this.newCelusPlatformShortName = new_value?.short_name;
      this.newCelusPlatformProvider = new_value?.provider;
      this.newCelusPlatformKnowledgebase = new_value?.knowledgebase;
      this.newCelusPlatformURL = new_value?.url;
    },
  },
};
</script>

<style>
:deep(.v-input__prepend) {
  pointer-events: auto;
  opacity: 1;
}
.subtitle {
  font-size: 80%;
  color: rgba(0, 0, 0, 0.5);
}
</style>
