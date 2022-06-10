import axios from "axios";

class ServerTask {
  constructor(taskId) {
    this.taskId = taskId;
    this.status = null;
    this.data = {};
  }

  get apiUrl() {
    return `/api/task-status/${this.taskId}/`;
  }

  get isFinished() {
    return ["SUCCESS", "FAILURE"].includes(this.status);
  }

  get isRunning() {
    return this.status === "STARTED";
  }

  get isPending() {
    return this.status === "PENDING";
  }

  get progressCurrent() {
    return this.data?.progress_current;
  }

  get progressTotal() {
    return this.data?.progress_total;
  }

  get progressPercentage() {
    if (this.progressTotal && this.progressCurrent !== null) {
      return (100 * this.progressCurrent) / this.progressTotal;
    }
    return null;
  }

  async getStatus() {
    try {
      let resp = await axios.get(this.apiUrl);
      this.data = resp.data;
      this.status = resp.data.status;
    } catch (error) {
      if (error.response?.status === 404) {
        // the task is not there, it may have been not created yet
        // (can happen if celery is done for example)
        this.status = "PENDING";
      }
    }
  }
}

export default ServerTask;
