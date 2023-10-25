<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("pages.events") }}</h2>
      </v-col>
      <!-- system notifications settings -->
      <v-col cols="auto">
        <v-tooltip
          v-if="notifyPermission === 'default'"
          bottom
          max-width="600px"
          key="default"
        >
          <template #activator="{ on }">
            <v-btn v-on="on" @click="askForPermission" color="primary">
              <v-icon small class="mr-1">fa-bell</v-icon>
              {{ $t("notifications.enable_notifications") }}
            </v-btn>
          </template>
          <span>{{ $t("notifications.enable_notifications_tt") }}</span>
        </v-tooltip>

        <v-tooltip
          v-else-if="notifyPermission === 'granted'"
          bottom
          max-width="600px"
          key="granted"
        >
          <template #activator="{ on }">
            <span v-on="on" class="text-button text--disabled">
              <v-icon small class="mr-1 text--disabled">fa-bell</v-icon>
              {{ $t("notifications.notifications_enabled") }}
            </span>
          </template>
          <span>{{ $t("notifications.notifications_enabled_tt") }}</span>
        </v-tooltip>

        <v-tooltip v-else bottom max-width="600px" key="denied">
          <template #activator="{ on }">
            <span v-on="on" class="text-button text--disabled">
              <v-icon small class="mr-1 text--disabled">fa-bell-slash</v-icon>
              {{ $t("notifications.notifications_disabled") }}
            </span>
          </template>
          <span>{{ $t("notifications.notifications_disabled_tt") }}</span>
        </v-tooltip>
      </v-col>
      <!-- event preferences - hidden for now -->
      <!--      <v-col cols="auto">-->
      <!--        <v-btn :to="{ name: 'event-preferences' }" color="secondary">-->
      <!--          {{ $t("pages.event_preferences") }}-->
      <!--        </v-btn>-->
      <!--      </v-col>-->
    </v-row>
    <v-row>
      <v-col>
        <EventList />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import EventList from "@/components/events/EventList.vue";

export default {
  name: "EventsPage",

  components: { EventList },

  data() {
    return {
      notifyPermission: Notification.permission,
    };
  },

  methods: {
    async askForPermission() {
      this.notifyPermission = await Notification.requestPermission();
    },
  },
};
</script>

<style scoped></style>
