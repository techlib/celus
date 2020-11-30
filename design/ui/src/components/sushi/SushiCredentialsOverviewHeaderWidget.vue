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
      <th class="text-left">{{ $t("credentials_name") }}:</th>
      <td>{{ credentialsName }}</td>
    </tr>
    <tr v-if="organization">
      <th class="text-left">{{ $t("organization") }}:</th>
      <td>{{ organization.name }}</td>
    </tr>
    <tr v-if="platform">
      <th class="text-left">{{ $t("platform") }}:</th>
      <td>{{ platform.name }}</td>
    </tr>
    <tr v-if="report">
      <th class="text-left">{{ $t("labels.report_type") }}:</th>
      <td>{{ report.name }}</td>
    </tr>
    <tr v-if="counterVersion">
      <th class="text-left">{{ $t("labels.counter_version") }}:</th>
      <td>{{ counterVersion }}</td>
    </tr>
    <tr v-if="month">
      <th class="text-left">{{ $t("month") }}:</th>
      <td>{{ month.name }}</td>
    </tr>
    <tr v-if="fromDate">
      <th class="text-left">{{ $t("not_older_than") }}:</th>
      <td>{{ fromDate }}</td>
    </tr>
  </table>
</template>

<script>
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
};
</script>
