function badge(item) {
  if (item.source) {
    if (item.source.organization) {
      return {
        color: "red",
        content: "badge.content.organization",
        tooltip: "badge.tooltip.organization",
      };
    }
  }
  return null;
}

export {
  badge,
};
