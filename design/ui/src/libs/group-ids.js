function parseGroupPart(part) {
  if (part.match(/^\d+$/)) {
    return Number.parseInt(part);
  } else if (part === "None") {
    return null;
  }
  return part;
}

function splitGroup(group) {
  if (group.substr(0, 4) === "grp-") {
    return group
      .substr(4)
      .split(/,/)
      .map((item) => parseGroupPart(item));
  }
}

export { splitGroup };
