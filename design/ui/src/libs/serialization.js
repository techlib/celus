function toBase64JSON(obj) {
  return Buffer.from(JSON.stringify(obj), "utf-8").toString("base64");
}

export { toBase64JSON };
