console.log("Worker: starting");

let ws = null; // websocket connection
let ports = []; // collects all ports connected to this worker
let lastNotifiedEventPk = null; // used to prevent duplicate notifications

onconnect = (e) => {
  // when a new tab/window connects to this worker
  let port = e.ports[0];
  ports.push(port);
  console.log("Worker: Port connected", port, "total ports", ports.length);

  port.onmessage = function (e) {
    // this takes care of messages from the main script
    console.log("Worker: Message received from main script", e.data);
    if (e.data.command === "startWs") {
      console.log("Starting Ws");
      startWs(e.data.token);
    } else if (e.data.command === "stopWs") {
      if (ws) {
        console.log("WS: Stopping connection");
        ws.close(4444); // private code to signal logout on FE side
        ws = null;
      }
    }
  };
};

function startWs(token) {
  // start websocket connection to the backend
  let wsProtocol = location.protocol === "https:" ? "wss" : "ws";
  if (!ws) {
    ws = new WebSocket(`${wsProtocol}://${location.host}/ws/`);

    ws.onopen = function () {
      console.log("WS: Connection opened");
      ws.send(
        JSON.stringify({
          command: "subscribe",
          data: token,
        }),
      );
    };

    ws.onmessage = function (e) {
      // this takes care of messages from the websocket server
      console.log("WS: Message received", e.data);
      let data = JSON.parse(e.data);
      if (data.event) {
        console.log(`WS: New event received. Pushing to ${ports.length} ports`);
        ports.forEach((port) =>
          port.postMessage({ type: "event", data: data }),
        );
        notify(data.event);
      } else if (data.type) {
        console.log(
          `WS: New ${data.type} received. Pushing to ${ports.length} ports`,
        );
        ports.forEach((port) => port.postMessage(data));
      }
    };

    ws.onclose = function (e) {
      console.log("WS: Connection closed", e.code);
      if (e.code === 1006) {
        // Connection closed abnormally
        // return;
      } else if (e.code === 1011 && ports.length > 0) {
        // Authentication error - we need to tell one of the connected ports
        // to request a new token. After that, the port will send a message
        // to this worker to start a new websocket connection, so we don't
        // need to do anything here.
        ports[0].postMessage({
          type: "wsAuthError",
          message: "Need new token",
        });
        ws = null;
        return;
      } else if (e.code === 4444) {
        // Logout on FE side, we do not want to reconnect
        return;
      }
      // some other error - try to reconnect
      console.log("WS: Reconnecting in 5 seconds...");
      ws = null;
      setTimeout(function () {
        startWs(token);
      }, 5000);
    };

    ws.onerror = function (e) {
      console.error("WS: Error", e);
    };
  }
}

async function notify(event) {
  // helper function - displays an event as a notification
  console.log("Notification permission: ", Notification.permission);
  if (Notification.permission === "default") {
    await Notification.requestPermission();
  }
  if (Notification.permission === "granted") {
    if (lastNotifiedEventPk !== event.pk) {
      new Notification("CELUS: new notification", {
        body: event.title,
        icon: "/favicon.png",
      });
      lastNotifiedEventPk = event.pk;
    } else {
      console.log("Notification already sent");
    }
  }
}

console.log("Worker: Finished loading");
