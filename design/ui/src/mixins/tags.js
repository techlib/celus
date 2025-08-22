import qs from "qs";

export default {
  data() {
    let tags = [];
    if (this.$route.query.tags) {
      if (typeof this.$route.query.tags === "number") {
        tags = [this.$route.query.tags];
      } else {
        tags = this.$route.query.tags
          .split(",")
          .map((x) => Number.parseInt(x, 10))
          .filter((x) => !!x);
      }
    }
    return {
      selectedTags: tags,
      objIdToTags: new Map(),
    };
  },

  methods: {
    cleanTagCache() {
      this.objIdToTags.clear();
    },
    async getTagsForObjectsById(objectType, objectIds) {
      let cleanObjectIds = objectIds.filter((x) => !this.objIdToTags.has(x));
      if (cleanObjectIds.length === 0) {
        return;
      }
      let objIdStr = cleanObjectIds.filter((x) => !!x).join(",");
      let linksPromise = this.http({
        url: "/api/tags/tag-item-links/",
        params: { item_type: objectType, item_id: objIdStr },
      });
      let tagsPromise = this.http({
        url: "/api/tags/tag/",
        params: { item_type: objectType, item_id: objIdStr },
      });
      let [linksResult, tagsResult] = await Promise.all([
        linksPromise,
        tagsPromise,
      ]);
      if (
        linksResult &&
        tagsResult &&
        !linksResult.error &&
        !tagsResult.error
      ) {
        let tagIdToObj = new Map();
        let newObjIdToTags = new Map(this.objIdToTags);

        tagsResult.response.data.forEach((tag) => tagIdToObj.set(tag.pk, tag));
        cleanObjectIds.forEach((id) => newObjIdToTags.set(id, []));
        linksResult.response.data.forEach((link) =>
          newObjIdToTags.get(link.target_id).push(tagIdToObj.get(link.tag_id)),
        );
        // we exchange the whole map to trigger a re-render
        this.objIdToTags = newObjIdToTags;
      }
    },
  },
};
