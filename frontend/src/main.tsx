import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/tokens.css";
import "./styles/caos.css";

const root = document.getElementById("root");
if (!root) throw new Error("no root element");
createRoot(root).render(
  <StrictMode>
    <h1 className="sr-only">CAOS</h1>
  </StrictMode>,
);
