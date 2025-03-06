<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <span>
    <span>{{ name }}</span
    >:
    <v-progress-circular
      v-if="loading"
      indeterminate
      size="16"
      color="disabled"
      width="1"
    ></v-progress-circular>
    <span v-else-if="valueType === 'text'" class="caption">{{ desc }}</span>
    <span v-else-if="valueType === 'tag'">
      <TagChip v-for="tag in values" :tag="tag" :key="tag.pk" small></TagChip>
    </span>
    <span v-else-if="valueType === 'tagClass'">
      <TagChip
        v-for="tagClass in values"
        :tag="tagClass"
        :key="tagClass.pk"
        small
        :show-class="false"
      ></TagChip>
    </span>
  </span>
</template>

<script>
import { smartMonthRange } from "@/libs/dates";
import translators from "@/mixins/translators";
import TagChip from "@/components/tags/TagChip.vue";

export default {
  name: "FilterSpec",
  components: { TagChip },

  mixins: [translators],

  props: {
    fltr: { type: Object },
  },

  data() {
    return {
      values: null,
      loading: false,
      valueType: "text",
    };
  },

  computed: {
    name() {
      return this.fltr.dimension.getName(this.$i18n);
    },
    desc() {
      if (this.valueType === "text") {
        if (this.values) {
          // these are values translated during the component's mounted() hook
          return this.values.join(", ");
        } else if (this.fltr.values) {
          return this.fltr.values.join(", ");
        } else if (this.fltr.start || this.fltr.end) {
          return smartMonthRange(this.fltr);
        }
      }
      return "-";
    },
  },

  async mounted() {
    this.loading = true;

    let translator = null;
    let toTranslate = [];
    if (this.fltr.values) {
      translator = this.getTranslator(this.fltr.dimension);
      toTranslate = this.fltr.values;
      if (translator) {
        await translator.prepareTranslation(toTranslate);
        this.values = toTranslate.map((item) =>
          translator.translateKeyToString(item, this.$i18n.locale),
        );
        this.values.sort((a, b) => a.localeCompare(b));
      }
    } else if (this.fltr.tag_ids || this.fltr.tag_class_ids) {
      // tags and tag classes get translated into objects, not strings
      translator = this.fltr.tag_ids
        ? this.translators.tag
        : this.translators.tagClass;
      toTranslate = this.fltr.tag_ids ?? this.fltr.tag_class_ids;
      this.valueType = this.fltr.tag_ids ? "tag" : "tagClass";
      await translator.prepareTranslation(toTranslate);
      this.values = toTranslate.map((item) =>
        translator.translateKey(item, this.$i18n.locale),
      );
    }

    this.loading = false;
  },
};
</script>
