import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";

import { getRouter } from "./router";
import "./styles.css";

const router = getRouter();

// The TanStack root route owns the complete document shell (`html`, `head`,
// and `body`), so the SPA entry must mount at the Document level.
createRoot(document).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
