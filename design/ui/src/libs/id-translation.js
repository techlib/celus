import axios from "axios";
import { itemToString } from "./db-object-localization";

class IdTranslation {
  constructor(apiUrl) {
    this.dict = new Map();
    this.url = apiUrl;
    this.toTranslate = new Set();
    this.stats = { hit: 0, miss: 0 };
    this.justUpdating = null;
  }

  translateKey(key) {
    if (this.dict.has(key)) {
      return this.dict.get(key);
    }
    this.toTranslate.add(key);
    return key;
  }

  translateKeyToString(key, locale = "en") {
    let item = this.translateKey(key);
    if (typeof item === "object") {
      return itemToString(item, locale);
    }
    return item;
  }

  async prepareTranslation(keys) {
    if (this.justUpdating) {
      await this.justUpdating;
    }
    // given a list of keys, the object should prepare data so that it can translate it
    for (let key of keys) {
      if (this.dict.has(key)) {
        this.stats.hit++;
      } else if (key) {
        this.toTranslate.add(key);
        this.stats.miss++;
      }
    }
    this.justUpdating = this.updateDictionary();
    await this.justUpdating;
    this.justUpdating = null;
  }

  async updateDictionary() {
    if (this.toTranslate.size > 0) {
      let pks = [...this.toTranslate].filter((item) => !!item).join(",");
      if (pks.length) {
        let url = this.url + `?pks=${pks}`;
        try {
          let response = await axios.get(url);
          let data = response.data;
          if ("results" in data) {
            data = data.results;
          }
          data.forEach((item) => {
            this.dict.set(item.pk, item);
            this.toTranslate.delete(item.pk);
          });
          // check if there are some untranslated items
          if (this.toTranslate.size > 0) {
            if ((response.data.count || 0) > response.data.results.length) {
              // this means that pagination prevented us from getting all the data
              // so we need to do another pass
              console.info(
                `Could not translate ${this.toTranslate.size} items; doing another pass`,
              );
              await this.updateDictionary();
            } else {
              console.info(
                `Could not translate ${this.toTranslate.size} items; giving up`,
              );
              this.toTranslate = new Set();
            }
          }
        } catch (error) {
          console.error(`Could not load ID translation from url "${url}"`);
        }
      }
    }
  }
}

export default IdTranslation;
