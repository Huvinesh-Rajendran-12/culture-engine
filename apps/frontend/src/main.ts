// Self-hosted fonts (latin subset only — no external network requests)
import "@fontsource/cinzel-decorative/latin-400.css";
import "@fontsource/cinzel-decorative/latin-700.css";
import "@fontsource/cinzel/latin-400.css";
import "@fontsource/cinzel/latin-600.css";
import "@fontsource/cinzel/latin-700.css";
import "@fontsource/eb-garamond/latin-400.css";
import "@fontsource/eb-garamond/latin-500.css";
import "@fontsource/eb-garamond/latin-600.css";
import "@fontsource/eb-garamond/latin-400-italic.css";
import "@fontsource/eb-garamond/latin-500-italic.css";
import "@fontsource/share-tech-mono/latin-400.css";

import { mount } from "svelte";
import App from "./App.svelte";

mount(App, { target: document.getElementById("root")! });
