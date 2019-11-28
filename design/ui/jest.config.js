module.exports = {
  verbose: true,
  roots: ["<rootDir>/src/", "<rootDir>/specs/"],
  moduleFileExtensions: ['js', 'vue'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  transform: {
    "^.+\\.js$": "babel-jest",
    "^.+\\.vue$": "vue-i18n-jest",
  },
  snapshotSerializers: [
    "<rootDir>/node_modules/jest-serializer-vue"
  ],
  collectCoverageFrom: ["src/**/*.{js,vue}", "!**/node_modules/**"],
  coverageReporters: ["text", "text-summary"]
}
