const DATA_UNTRIED = "untried";
const DATA_FAILED = "failed";
const DATA_NO_DATA = "no_data";
const DATA_PARTIAL_DATA = "partial_data";
const DATA_SUCCESS = "success";

function dataStateToIcon(state) {
  switch (state) {
    case DATA_UNTRIED:
      return { color: "secondary", icon: "far fa-circle" };
    case DATA_FAILED:
      return { color: "error", icon: "fas fa-exclamation-circle" };
    case DATA_NO_DATA:
      return { color: "success", icon: "far fa-circle" };
    case DATA_SUCCESS:
      return { color: "success", icon: "far fa-check-circle" };
    case DATA_PARTIAL_DATA:
      return { color: "warning", icon: "fas fa-exclamation-triangle" };
    default:
      return { color: "warning", icon: "far fa-question-circle" };
  }
}

export {
  dataStateToIcon,
  DATA_UNTRIED,
  DATA_FAILED,
  DATA_NO_DATA,
  DATA_SUCCESS,
  DATA_PARTIAL_DATA,
};
