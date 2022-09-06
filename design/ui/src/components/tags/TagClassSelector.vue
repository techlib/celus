<i18n lang="yaml" src="../../locales/common.yaml"></i18n>

<template>
  <v-autocomplete
    v-model="tagClass"
    :items="tagClasses"
    item-text="name"
    item-value="pk"
    return-object
    :loading="tagClassesLoading"
    :label="realLabel"
    :rules="clearable ? [] : [rules.required]"
    :disabled="disabled"
    :clearable="clearable"
    clear-icon="fa-times"
    :placeholder="placeholder"
    :persistent-placeholder="!!placeholder"
  >
    <template #item="{ item }">
      <v-list-item-content>
        <v-list-item-title>
          {{ item.name }}
          <span class="float-right text-caption">{{ $t(item.scope) }}</span>
        </v-list-item-title>
      </v-list-item-content>
    </template>

    <template #append-item v-if="allowCreate">
      <v-list-item-content>
        <v-list-item-title>
          <AddTagClassButton small class="ml-4" @saved="assignNewClass" />
        </v-list-item-title>
      </v-list-item-content>
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
    value: { type: [Object, Number], required: false },
    disabled: { type: Boolean, default: false },
    scope: { type: String, required: false },
    clearable: { type: Boolean, default: false },
    label: { type: String, default: "" },
    placeholder: { type: String, default: "" },
    allowCreate: { type: Boolean, default: false },
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
      const url = "/api/tags/tag-class/";
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
        if (typeof this.value === "number") {
          // if tag-class was given as a number, translate it to the object
          this.tagClass = this.tagClasses.find(
            (tagClass) => tagClass.pk === this.value
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
      this.$emit("input", this.tagClass);
    },
    value: {
      handler() {
        this.tagClass = this.value;
      },
      immediate: true,
    },
    url() {
      this.fetchTagClasses();
    },
  },
};
</script>
