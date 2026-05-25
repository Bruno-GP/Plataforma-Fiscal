import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-sky-400/70 focus:ring-offset-2 focus:ring-offset-background",
  {
    variants: {
      variant: {
        default: "border-emerald-400/35 bg-emerald-400/14 text-emerald-300 hover:bg-emerald-400/20",
        secondary: "border-sky-400/35 bg-sky-400/14 text-sky-300 hover:bg-sky-400/20",
        destructive: "border-rose-400/35 bg-rose-400/14 text-rose-300 hover:bg-rose-400/20",
        outline: "border-slate-600 bg-slate-900/55 text-slate-300",
        warning: "border-amber-400/35 bg-amber-400/14 text-amber-300 hover:bg-amber-400/20",
        purple: "border-violet-400/35 bg-violet-400/14 text-violet-300 hover:bg-violet-400/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
