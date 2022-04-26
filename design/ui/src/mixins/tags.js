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
    async getTagsForObjectsById(objectType, objectIds) {
      let linksPromise = this.http({
        url: "/api/tags/tag-item-links/",
        params: { item_type: objectType, item_id: objectIds },
        paramsSerializer: function (params) {
          return qs.stringify(params, { arrayFormat: "repeat" });
        },
      });
      let tagsPromise = this.http({
        url: "/api/tags/tag/",
        params: { item_type: objectType, item_id: objectIds },
        paramsSerializer: function (params) {
          return qs.stringify(params, { arrayFormat: "repeat" });
        },
      });
      let [linksResult, tagsResult] = await Promise.all([
        linksPromise,
        tagsPromise,
      ]);
      if (!linksResult.error && !tagsResult.error) {
        let tagIdToObj = new Map();
        tagsResult.response.data.forEach((tag) => tagIdToObj.set(tag.pk, tag));
        let objIdToTags = new Map();
        objectIds.forEach((id) => objIdToTags.set(id, []));
        linksResult.response.data.forEach((link) =>
          objIdToTags.get(link.target_id).push(tagIdToObj.get(link.tag_id))
        );
        this.objIdToTags = objIdToTags;
      }
    },
  },
};
