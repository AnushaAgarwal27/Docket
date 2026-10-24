/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as activity from "../activity.js";
import type * as cartesia from "../cartesia.js";
import type * as cases from "../cases.js";
import type * as dashboard from "../dashboard.js";
import type * as files from "../files.js";
import type * as flags from "../flags.js";
import type * as http from "../http.js";
import type * as patterns from "../patterns.js";
import type * as paystubs from "../paystubs.js";
import type * as profiles from "../profiles.js";
import type * as seed from "../seed.js";
import type * as sources from "../sources.js";
import type * as timeline from "../timeline.js";
import type * as transactions from "../transactions.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  activity: typeof activity;
  cartesia: typeof cartesia;
  cases: typeof cases;
  dashboard: typeof dashboard;
  files: typeof files;
  flags: typeof flags;
  http: typeof http;
  patterns: typeof patterns;
  paystubs: typeof paystubs;
  profiles: typeof profiles;
  seed: typeof seed;
  sources: typeof sources;
  timeline: typeof timeline;
  transactions: typeof transactions;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};
