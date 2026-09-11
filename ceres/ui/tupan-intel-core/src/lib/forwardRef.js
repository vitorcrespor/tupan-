import * as React from "react";

/**
 * Props for legacy JS adapters that transparently forward native or Radix
 * attributes. The index signature is deliberate: these wrappers preserve the
 * complete upstream prop surface while their implementation remains JSX.
 *
 * @typedef {{
 *   children?: React.ReactNode,
 *   className?: string,
 *   [key: string]: any,
 * }} ForwardedProps
 */

/**
 * Gives legacy JSX wrappers an explicit React 19 prop contract.
 *
 * @param {(props: ForwardedProps, ref: React.ForwardedRef<any>) => React.ReactNode} render
 * @returns {React.ForwardRefExoticComponent<React.PropsWithoutRef<ForwardedProps> & React.RefAttributes<any>>}
 */
export function forwardRef(render) {
  return React.forwardRef(render);
}