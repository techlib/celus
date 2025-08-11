interface PlatformBasic {
  id: number;
  name: string;
  short_name: string;
}

interface ReportTypeBasic {
  id: number;
  short_name: string;
  name: string;
}

interface AnomalyReason {
  target_id_text: string;
  type: string;
  median: number;
  total_value: number;
  group_count: number;
  dim: string;
}

interface Anomaly {
  id: number;
  date: string;
  platform: PlatformBasic;
  organization: string;
  reportType: ReportTypeBasic;
  metric: string;
  organizationId: number;
  metricId: number;
  value: number;
  median: number;
  lowerBound: number;
  upperBound: number;
  differenceFromMedian: number;
  history: Record<string, number>;
  significance: number;
}

export type { PlatformBasic, ReportTypeBasic, AnomalyReason, Anomaly };
