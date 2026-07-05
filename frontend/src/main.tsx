import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import { FloatingPrompt } from "./components/FloatingPrompt";
import "./index.css";
import { initSyncEngine } from "./network/syncEngine";

// Boot the WebSocket sync engine (auto-reconnects)
initSyncEngine();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <HashRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/popup/prompt" element={<FloatingPrompt />} />
      </Routes>
    </HashRouter>
  </React.StrictMode>,
);
