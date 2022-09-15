const accessLevels = {
  EVERYBODY: 10,
  ORG_USERS: 20,
  ORG_ADMINS: 30,
  CONS_ADMINS: 40,
  OWNER: 50,
  SYSTEM: 100,
};

function tagText(tag) {
  if (typeof tag === "string") {
    return tag;
  }
  return `${tag.tag_class.name} / ${tag.name}`;
}

export { accessLevels, tagText };
