<i18n lang="yaml" src="@/locales/common.yaml" />

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <v-select
          v-model="command"
          :items="commands"
          :label="$t('labels.select_command')"
          item-text="name"
          return-object
        >
          <template #item="{ item }">
            <v-list-item-content>
              <v-list-item-title>{{ item.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ item.help }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row v-if="command">
      <v-col>
        <ManagementCommand :command="command" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { defineComponent } from "vue";
import cancellation from "@/mixins/cancellation";
import ManagementCommand from "@/components/admin/ManagementCommand.vue";

export default defineComponent({
  name: "ManagementCommandList",

  mixins: [cancellation],

  components: { ManagementCommand },

  data() {
    return {
      commands: [],
      command: null,
    };
  },

  methods: {
    async fetchCommands() {
      const result = await this.http({
        url: "/api/management/command",
      });
      if (!result.error) {
        this.commands = result.response.data;
      }
    },
  },

  created() {
    this.fetchCommands();
  },
});
</script>

<style scoped lang="scss"></style>
