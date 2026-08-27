import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export const AnimatedBeam = React.forwardRef(
  (
    {
      className,
      containerRef,
      fromRef,
      toRef,
      curvature = 0,
      reverse = false,
      pathWidth = 2,
      pathColor = "gray",
      pathOpacity = 0.2,
      gradientStartColor = "#18CCFC",
      gradientStopColor = "#6344F5",
      delay = 0,
      duration = 4,
      active = true,
      startXOffset = 0,
      startYOffset = 0,
      endXOffset = 0,
      endYOffset = 0,
      width = 200,
      height = 200,
    },
    ref
  ) => {
    const id = React.useId();
    const [pathD, setPathD] = React.useState("");
    const [svgWidth, setSvgWidth] = React.useState(width);
    const [svgHeight, setSvgHeight] = React.useState(height);
    const [gradientCoords, setGradientCoords] = React.useState({
      x1: "0%",
      x2: "0%",
      y1: "0%",
      y2: "0%",
    });

    React.useEffect(() => {
      const updatePath = () => {
        if (containerRef.current && fromRef.current && toRef.current) {
          const containerRect = containerRef.current.getBoundingClientRect();
          const fromRect = fromRef.current.getBoundingClientRect();
          const toRect = toRef.current.getBoundingClientRect();

          const coordinates = [
            {
              x: fromRect.left - containerRect.left + fromRect.width / 2,
              y: fromRect.top - containerRect.top + fromRect.height / 2,
            },
            {
              x: toRect.left - containerRect.left + toRect.width / 2,
              y: toRect.top - containerRect.top + toRect.height / 2,
            },
          ];

          const dx = coordinates[1].x - coordinates[0].x;
          const dy = coordinates[1].y - coordinates[0].y;
          const len = Math.hypot(dx, dy) || 1;
          const perpX = -dy / len;
          const perpY = dx / len;
          const midX = (coordinates[0].x + coordinates[1].x) / 2 + (startXOffset + endXOffset) / 2;
          const midY = (coordinates[0].y + coordinates[1].y) / 2 + (startYOffset + endYOffset) / 2;
          const ctrlX = midX + perpX * curvature;
          const ctrlY = midY + perpY * curvature;

          const d = `M ${coordinates[0].x},${coordinates[0].y} Q ${ctrlX},${ctrlY} ${coordinates[1].x},${coordinates[1].y}`;
          setPathD(d);

          setSvgWidth(containerRect.width);
          setSvgHeight(containerRect.height);

          setGradientCoords({
            x1: `${(coordinates[0].x / containerRect.width) * 100}%`,
            y1: `${(coordinates[0].y / containerRect.height) * 100}%`,
            x2: `${(coordinates[1].x / containerRect.width) * 100}%`,
            y2: `${(coordinates[1].y / containerRect.height) * 100}%`,
          });
        }
      };

      const resizeObserver = new ResizeObserver(updatePath);
      if (containerRef.current) resizeObserver.observe(containerRef.current);
      if (fromRef.current) resizeObserver.observe(fromRef.current);
      if (toRef.current) resizeObserver.observe(toRef.current);
      updatePath();

      return () => resizeObserver.disconnect();
    }, [
      containerRef,
      fromRef,
      toRef,
      curvature,
      startXOffset,
      startYOffset,
      endXOffset,
      endYOffset,
    ]);

    return (
      <svg
        ref={ref}
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className={cn("pointer-events-none absolute left-0 top-0", className)}
        fill="none"
      >
        <path
          d={pathD}
          stroke={pathColor}
          strokeWidth={pathWidth}
          strokeOpacity={pathOpacity}
          strokeDasharray="8 4"
        />
        <defs>
          <linearGradient
            id={id}
            gradientUnits="userSpaceOnUse"
            x1={gradientCoords.x1}
            y1={gradientCoords.y1}
            x2={gradientCoords.x2}
            y2={gradientCoords.y2}
          >
            {reverse ? (
              <>
                <stop offset="0%" stopColor={gradientStopColor} />
                <stop offset="100%" stopColor={gradientStartColor} />
              </>
            ) : (
              <>
                <stop offset="0%" stopColor={gradientStartColor} />
                <stop offset="100%" stopColor={gradientStopColor} />
              </>
            )}
          </linearGradient>
        </defs>
        <motion.path
          d={pathD}
          strokeWidth={pathWidth}
          stroke={`url(#${id})`}
          fill="none"
          strokeLinecap="round"
          initial={false}
          animate={active ? { opacity: [0.1, 0.85, 0.1] } : { opacity: 0.08 }}
          transition={
            active
              ? { duration, ease: "easeInOut", repeat: Infinity, delay }
              : { duration: 0.4, ease: "easeOut" }
          }
        />
      </svg>
    );
  }
);

AnimatedBeam.displayName = "AnimatedBeam";

export default AnimatedBeam;