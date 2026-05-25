import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(  
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold ring-offset-background transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-sky-500 text-slate-950 shadow-[0_14px_32px_-20px_rgba(56,189,248,0.95)] hover:bg-sky-400 active:bg-sky-500",
        destructive: "bg-rose-500 text-slate-950 shadow-[0_14px_32px_-20px_rgba(248,113,113,0.8)] hover:bg-rose-400 active:bg-rose-500",
        outline: "border border-slate-700 bg-slate-950/45 text-slate-100 hover:border-sky-500/70 hover:bg-slate-900 active:bg-slate-800",
        secondary: "border border-slate-700 bg-slate-800/90 text-slate-100 hover:border-slate-600 hover:bg-slate-700 active:bg-slate-800",
        ghost: "text-slate-300 hover:bg-slate-800/75 hover:text-slate-50 active:bg-slate-800",
        link: "text-sky-300 underline-offset-4 hover:text-sky-200 hover:underline",
        success: "bg-emerald-500 text-slate-950 shadow-[0_14px_32px_-20px_rgba(52,211,153,0.85)] hover:bg-emerald-400 active:bg-emerald-500",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
