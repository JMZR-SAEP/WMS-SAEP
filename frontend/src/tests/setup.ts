import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

import { appQueryClient } from "../app/query-client";

window.scrollTo = () => {};

afterEach(async () => {
  await appQueryClient.cancelQueries();
  appQueryClient.clear();
});
