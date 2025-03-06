<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  not_older_than: Not older than
  credentials_name: Name of credentials

cs:
  not_older_than: Ne starší než
  credentials_name: Jméno přístupových údajů
</i18n>

<template>
  <table class="overview">
    <tr v-if="credentialsName">
      <th class="text-left text-medium-emphasis">
        {{ $t("credentials_name") }}:
      </th>
      <td class="text-medium-emphasis">{{ credentialsName }}</td>
    </tr>
    <tr v-if="organization">
      <th class="text-left text-medium-emphasis">{{ $t("organization") }}:</th>
      <td class="text-medium-emphasis">{{ organization.name }}</td>
    </tr>
    <tr v-if="platform">
      <th class="text-left text-medium-emphasis">{{ $t("platform") }}:</th>
      <td class="text-medium-emphasis">{{ platform.name }}</td>
    </tr>
    <tr v-if="report">
      <th class="text-left text-medium-emphasis">
        {{ $t("labels.report_type") }}:
      </th>
      <td class="text-medium-emphasis">{{ report.name }}</td>
    </tr>
    <tr v-if="counterVersion">
      <th class="text-left text-medium-emphasis">
        {{ $t("labels.counter_version") }}:
      </th>
      <td class="text-medium-emphasis">
        {{ counterVersionToStr(counterVersion) }}
      </td>
    </tr>
    <tr v-if="month">
      <th class="text-left text-medium-emphasis">{{ $t("month") }}:</th>
      <td class="text-medium-emphasis">{{ month.name }}</td>
    </tr>
    <tr v-if="fromDate">
      <th class="text-left text-medium-emphasis">
        {{ $t("not_older_than") }}:
      </th>
      <td class="text-medium-emphasis">{{ fromDate }}</td>
    </tr>
  </table>
</template>

<script>
import { counterVersionToStr } from "@/libs/sushi";

export default {
  name: "SushiCredentialsOverviewHeaderWidget",
  props: {
    credentialsName: { required: false },
    organization: { required: false },
    platform: { required: false },
    report: { required: false },
    fromDate: { required: false },
    month: { required: false },
    counterVersion: { required: false },
  },
  methods: {
    counterVersionToStr(value) {
      return counterVersionToStr(value);
    },
  },
};
</script>
