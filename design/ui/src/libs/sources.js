function badge(item) {
  if (item.source && item.source.organization) {
    return {
      color: "red",
      content: "badge.content.organization",
      tooltip: "badge.tooltip.organization",
    };
  }
  if (item.counter_registry_id) {
    return {
      color: "counterRegistry",
      content: "badge.content.registry",
      tooltip: "badge.tooltip.registry",
    };
  }
  return null;
}

export { badge };
