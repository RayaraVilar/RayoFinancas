import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-11 w-full rounded-xl border border-[#d9e2db] bg-white px-3.5 py-2 text-sm text-[#173f35] outline-none transition placeholder:text-[#9aa69f] focus:border-[#7f9c8d] focus:ring-2 focus:ring-[#dce9df] disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
