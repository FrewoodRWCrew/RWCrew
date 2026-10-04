// A plain native <select>, styled like the other inputs. On a phone it opens
// the system's own picker (the scroll wheel on an iPhone), which is easier
// to use with a thumb than a dropdown drawn inside the page.

import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function PhoneSelect({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-md border border-input bg-background px-3 text-base disabled:opacity-60",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
