<i18n lang="yaml">
en:
  more: more | more | more

cs:
  more: další | další | dalších
</i18n>

<template>
  <div>
    <div
      v-for="group in groups"
      :key="group.pk"
      :class="
        highlightGroupId && group.pk === highlightGroupId
          ? 'green--text font-weight-medium'
          : ''
      "
    >
      <span class="pr-2">{{ group.name }}:</span>
      <MetricChip
        v-for="metric in group.metrics"
        :key="`${group.pk}-${metric.pk}`"
        :metric="metric"
      />
      <span v-if="group.extra" class="text-caption">
        +{{ group.extra }} {{ $tc("more", group.extra) }}
      </span>
    </div>
  </div>
</template>
<script>
import MetricChip from "@/components/reporting/MetricChip";

export default {
  name: "ReportInterestGroups",

  components: { MetricChip },

  props: {
    report: { type: Object },
    highlightGroupId: { type: Number, required: false, default: null },
    maxCount: { type: Number, default: null, required: false },
  },

  computed: {
    groups() {
      let groupSet = new Map();
      this.report.interest_metric_set.forEach((im) =>
        groupSet.set(im.interest_group.pk, im.interest_group)
      );
      let groups = [...groupSet.values()];
      groups.forEach((group) => {
        group.metrics = [];
        this.report.interest_metric_set
          .filter((im) => im.interest_group.pk === group.pk)
          .forEach((im) => group.metrics.push(im.metric));
        // shorten the list of metrics if requested
        if (group.metrics.length > this.maxCount) {
          group.extra = group.metrics.length - this.maxCount;
          group.metrics = group.metrics.slice(0, this.maxCount);
        }
      });
      groups.sort((a, b) => a.name.localeCompare(b.name));
      return groups;
    },
  },
};
</script>
