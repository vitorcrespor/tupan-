import * as React from "react"

import { cn } from "@/lib/utils"
import { forwardRef } from "@/lib/forwardRef"

const Input = forwardRef(({ className, type, ...props }, ref) => {
  return (
    (<input
      type={type}
      className={cn(
        "field-control flex h-9 w-full min-w-0 px-3 py-1 text-base transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground disabled:opacity-50 md:text-sm",
        className
      )}
      ref={ref}
      {...props} />)
  );
})
Input.displayName = "Input"

export { Input }
