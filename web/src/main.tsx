import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app";
import "./style.css";

const container = document.querySelector("#root");

if (!container) {
  throw new Error("The application root element is missing.");
}

createRoot(container).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
