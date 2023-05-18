function getProba(stats, x) {
  let lastX = 0;
  let lastProba = 0;
  for (let i = 0; i < stats.curve.length; i++) {
    if (stats.curve[i] >= x) {
      return (
        lastProba +
        ((x - lastX) / (stats.curve[i] - lastX)) *
          (stats.probabs[i] - lastProba)
      );
    }
    lastX = stats.curve[i];
    lastProba = stats.probabs[i];
  }
  return 1;
}

function getDayForProba(stats, proba) {
  let lastX = 0;
  let lastProba = 0;
  for (let i = 0; i < stats.curve.length; i++) {
    if (stats.probabs[i] >= proba) {
      return (
        lastX +
        ((proba - lastProba) / (stats.probabs[i] - lastProba)) *
          (stats.curve[i] - lastX)
      );
    }
    lastX = stats.curve[i];
    lastProba = stats.probabs[i];
  }
  return stats.curve[stats.curve.length - 1];
}

export { getProba, getDayForProba };
