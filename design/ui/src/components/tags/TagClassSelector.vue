<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    v-model="tagClass"
    :items="tagClasses"
    item-title="name"
    item-value="pk"
    return-object
    :loading="tagClassesLoading"
    :label="realLabel"
    :rules="clearable ? [] : [rules.required]"
    :disabled="disabled"
    :clearable="clearable"
    clear-icon="fa fa-times"
    :placeholder="placeholder"
    :persistent-placeholder="!!placeholder"
    :menu-props="{ eager: true }"
  >
    <template v-slot:item="{ props, item }">
      <v-list-item
        v-bind="props"
        class="d-flex align-center justify-space-between"
      >
        <template v-slot:append>
          <span class="text-caption">{{ $t(item.raw.scope) }}</span>
        </template>
      </v-list-item>
    </template>
    <template #prepend v-if="tooltip">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-icon v-bind="props">fa fa-info-circle</v-icon>
        </template>
        {{ tooltip }}
      </v-tooltip>
    </template>
    <template #append-item v-if="allowCreate">
      <v-list-item>
        <v-list-item-title>
          <AddTagClassButton
            small
            class="ml-4"
            @saved="assignNewClass"
            :scope="scope"
            text
            outlined
          ></AddTagClassButton>
        </v-list-item-title>
      </v-list-item>
    </template>
    <template #prepend v-if="showIcon">
      <v-icon size="small">fa fa-tags fa-fw</v-icon>
    </template>
  </v-autocomplete>
</template>

<script>
import AddTagClassButton from "@/components/tags/AddTagClassButton";
import formRulesMixin from "@/mixins/formRulesMixin";
import cancellation from "@/mixins/cancellation";

export default {
  name: "TagClassSelector",

  components: { AddTagClassButton },

  mixins: [cancellation, formRulesMixin],

  props: {
    modelValue: { type: [Object, Number, String], required: false },
    disabled: { type: Boolean, default: false },
    scope: {
      type: String,
      required: false,
      validator: (modelValue) =>
        ["title", "platform", "organization"].includes(modelValue),
    },
    clearable: { type: Boolean, default: false },
    label: { type: String, default: "" },
    placeholder: { type: String, default: "" },
    allowCreate: { type: Boolean, default: false },
    withVisibleTags: { type: Boolean, default: false },
    showIcon: { type: Boolean, default: false },
    tooltip: { type: String, default: "" },
  },

  data() {
    return {
      tagClass: null,
      tagClasses: [],
      tagClassesLoading: false,
    };
  },

  computed: {
    url() {
      let url = "/api/tags/tag-class/";
      if (this.withVisibleTags) {
        url += "visible-tags/";
      }
      if (this.scope) {
        return url + "?scope=" + this.scope;
      } else {
        return url;
      }
    },
    realLabel() {
      if (this.label) {
        return this.label;
      } else {
        return this.$t("labels.tag_class");
      }
    },
  },

  methods: {
    async fetchTagClasses() {
      this.tagClassesLoading = true;
      const reply = await this.http({ url: this.url });
      this.tagClassesLoading = false;
      if (!reply.error) {
        this.tagClasses = reply.response.data;
        if (typeof this.modelValue === "number") {
          // if tag-class was given as a number, translate it to the object
          this.tagClass = this.tagClasses.find(
            (tagClass) => tagClass.pk === this.modelValue,
          );
        }
      }
    },
    assignNewClass(newClass) {
      this.tagClasses.push(newClass);
      this.tagClasses.sort((a, b) => a.name.localeCompare(b.name));
      this.tagClass = newClass;
    },
    async reload() {
      await this.fetchTagClasses();
    },
  },

  mounted() {
    this.fetchTagClasses();
  },

  watch: {
    tagClass() {
      this.$emit("update:modelValue", this.tagClass);
    },
    modelValue: {
      handler() {
        this.tagClass = this.modelValue;
      },
      immediate: true,
    },
    url() {
      this.fetchTagClasses();
    },
  },
};
</script>
