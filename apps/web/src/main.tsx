import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import AuthGate from "./auth/AuthGate";
import "./styles.css";
import "./decision-intelligence.css";
import "./professional-ui.css";
import "./enterprise-dashboard.css";
import "./executive-overrides.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthGate><App /></AuthGate>
  </React.StrictMode>
);
