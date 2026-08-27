import { ChevronDownIcon, ChevronUpIcon, MinusIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Pill({ variant = "secondary", themed = false, className, ...props }) {
  return (
    <Badge
      variant={variant}
      className={cn(
        "h-7 gap-1.5 rounded-full pl-2 pr-3 text-xs font-medium",
        themed && "border-primary/20 bg-primary/10 text-primary",
        className
      )}
      {...props}
    />
  );
}

export function PillAvatar({ fallback, className, children, ...props }) {
  return (
    <Avatar className={cn("size-4", className)} {...props}>
      {children}
      <AvatarFallback>{fallback}</AvatarFallback>
    </Avatar>
  );
}

export function PillButton({ className, ...props }) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={cn("size-4 rounded-full", className)}
      {...props}
    />
  );
}

export function PillStatus({ children, className, ...props }) {
  return (
    <span className={cn("text-xs text-muted-foreground", className)} {...props}>
      {children}
    </span>
  );
}

export function PillIndicator({ variant = "success", pulse = false }) {
  const colors = {
    success: "bg-emerald-500",
    error: "bg-red-500",
    warning: "bg-amber-500",
    info: "bg-blue-500",
  };
  return (
    <span className="relative flex size-2">
      {pulse && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
            colors[variant]
          )}
        />
      )}
      <span className={cn("relative inline-flex size-2 rounded-full", colors[variant])} />
    </span>
  );
}

export function PillDelta({ className, delta }) {
  if (!delta) {
    return <MinusIcon className={cn("size-3 text-muted-foreground", className)} />;
  }
  if (delta > 0) {
    return (
      <div className={cn("flex items-center gap-0.5 text-emerald-500", className)}>
        <ChevronUpIcon className="size-3" />
        <span className="text-xs tabular-nums">{delta}</span>
      </div>
    );
  }
  return (
    <div className={cn("flex items-center gap-0.5 text-red-500", className)}>
      <ChevronDownIcon className="size-3" />
      <span className="text-xs tabular-nums">{Math.abs(delta)}</span>
    </div>
  );
}

export function PillIcon({ icon: Icon, className, ...props }) {
  return <Icon className={cn("size-3.5", className)} {...props} />;
}

export function PillAvatarGroup({ children, className, ...props }) {
  return (
    <div
      className={cn(
        "flex items-center [&>*:not(:first-of-type)]:[mask-image:radial-gradient(circle_9px_at_-4px_50%,transparent_99%,white_100%)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}