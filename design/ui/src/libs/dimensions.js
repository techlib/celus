const explicitDimensionCount = 8;
const explicitDimensions = [];

for (let i = 0; i < explicitDimensionCount; i++) {
  explicitDimensions.push(`dim${i + 1}`);
}

export { explicitDimensions, explicitDimensionCount };
