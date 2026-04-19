import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { initSyncEngine } from "./network/syncEngine";

// Boot the WebSocket sync engine (auto-reconnects)
initSyncEngine();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
