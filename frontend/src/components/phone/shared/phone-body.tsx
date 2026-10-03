// The scrolling content area under a PhoneHeader: comfortable side padding,
// and room at the bottom for the iPhone's home indicator.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PhoneBodyProps {
  children: ReactNode;
  className?: string;
}

export function PhoneBody({ children, className }: PhoneBodyProps) {
  return (
    <main className={cn("flex flex-1 flex-col gap-4 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]", className)}>
      {children}
    </main>
  );
}
