import * as React from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "rounded-[24px] border border-[#e0e8e1] bg-white p-6 shadow-[0_18px_50px_rgba(23,63,53,.06)]",
        className,
      )}
      {...props}
    />
  );
}
