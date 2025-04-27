import React, { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
  viewportClassName?: string;
}

/**
 * 滚动区域组件
 * 提供自定义样式的可滚动区域，支持自动隐藏的滚动条
 */
const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ children, className, viewportClassName, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("relative overflow-hidden", className)}
        {...props}
      >
        <div
          className={cn(
            "h-full w-full overflow-auto scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-slate-800/50 scrollbar-thumb-rounded",
            viewportClassName
          )}
        >
          {children}
        </div>
      </div>
    );
  }
);

ScrollArea.displayName = "ScrollArea";

export { ScrollArea };
