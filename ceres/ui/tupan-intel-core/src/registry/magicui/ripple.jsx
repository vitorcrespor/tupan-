import React from "react";
import { cn } from "@/lib/utils";

export function Ripple({
  mainCircleSize = 220,
  numCircles = 8,
  step = 44,
  className,
  color = "188 78% 52%",
}) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 select-none", className)}>
      {Array.from({ length: numCircles }, (_, i) => {
        const size = mainCircleSize + i * step;
        const opacity = 0.5 - (i * 0.5) / numCircles;
        const animationDelay = `${i * 0.12}s`;
        return (
          <div
            key={i}
            className="absolute animate-ripple rounded-full border"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              opacity,
              animationDelay,
              borderWidth: "1px",
              left: "50%",
              top: "50%",
              transform: "translate(-50%, -50%)",
              borderColor: `hsl(${color} / ${0.28 + i * 0.03})`,
              backgroundColor: `hsl(${color} / 0.035)`,
            }}
          />
        );
      })}
    </div>
  );
}

export default Ripple;