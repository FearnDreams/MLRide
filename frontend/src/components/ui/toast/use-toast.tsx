import * as React from "react"
import * as ToastPrimitives from "@radix-ui/react-toast"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"

import { cn } from "../../../lib/utils"

const TOAST_LIMIT = 5

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border border-slate-700 p-6 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full",
  {
    variants: {
      variant: {
        default: "bg-slate-800 text-slate-300",
        destructive: "border-red-800 bg-red-900 text-slate-50",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export const Toast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Root> &
    VariantProps<typeof toastVariants>
>(({ className, variant, ...props }, ref) => {
  return (
    <ToastPrimitives.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  )
})
Toast.displayName = ToastPrimitives.Root.displayName

export const ToastAction = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Action>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Action>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Action
    ref={ref}
    className={cn(
      "inline-flex h-8 shrink-0 items-center justify-center rounded-md border border-slate-700 bg-transparent px-3 text-sm font-medium ring-offset-slate-900 transition-colors hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 group-[.destructive]:border-slate-500/40 group-[.destructive]:hover:border-red-900/30 group-[.destructive]:hover:bg-red-900 group-[.destructive]:hover:text-slate-50 group-[.destructive]:focus:ring-red-900",
      className
    )}
    {...props}
  />
))
ToastAction.displayName = ToastPrimitives.Action.displayName

export const ToastClose = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Close>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Close
    ref={ref}
    className={cn(
      "absolute right-2 top-2 rounded-md p-1 text-slate-400 opacity-0 transition-opacity hover:text-slate-50 focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100 group-[.destructive]:text-red-300 group-[.destructive]:hover:text-red-50 group-[.destructive]:focus:ring-red-400 group-[.destructive]:focus:ring-offset-red-600",
      className
    )}
    toast-close=""
    {...props}
  >
    <X className="h-4 w-4" />
  </ToastPrimitives.Close>
))
ToastClose.displayName = ToastPrimitives.Close.displayName

export const ToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Title
    ref={ref}
    className={cn("text-sm font-semibold", className)}
    {...props}
  />
))
ToastTitle.displayName = ToastPrimitives.Title.displayName

export const ToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Description
    ref={ref}
    className={cn("text-sm opacity-90", className)}
    {...props}
  />
))
ToastDescription.displayName = ToastPrimitives.Description.displayName

export const ToastProvider = ToastPrimitives.Provider

export const ToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Viewport
    ref={ref}
    className={cn(
      "fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]",
      className
    )}
    {...props}
  />
))
ToastViewport.displayName = ToastPrimitives.Viewport.displayName

// 定义我们自己的ToastProps类型，用于useToast钩子
export interface ToastProps {
  id?: string
  title?: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  variant?: "default" | "destructive"
  open?: boolean
}

// 状态容器
const TOAST_STATE = {
  toasts: [] as Array<ToastProps & { id: string; open: boolean }>,
  listeners: new Set<() => void>(),
}

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

function dispatch() {
  TOAST_STATE.listeners.forEach((listener) => listener())
}

export function useToast() {
  const [toasts, setToasts] = React.useState(TOAST_STATE.toasts)
  
  // 侦听状态变化
  React.useEffect(() => {
    const listener = () => {
      setToasts([...TOAST_STATE.toasts])
    }
    
    TOAST_STATE.listeners.add(listener)
    return () => {
      TOAST_STATE.listeners.delete(listener)
    }
  }, [])
  
  return {
    toasts,
    toast: (props: Omit<ToastProps, "id" | "open">) => {
      const id = generateId()
      
      const newToast = {
        ...props,
        id,
        open: true,
      }
      
      TOAST_STATE.toasts = [newToast, ...TOAST_STATE.toasts].slice(0, TOAST_LIMIT)
      dispatch()
      
      return id
    },
    dismiss: (id: string) => {
      TOAST_STATE.toasts = TOAST_STATE.toasts.filter((toast) => toast.id !== id)
      dispatch()
    },
    update: (id: string, props: Partial<Omit<ToastProps, "id">>) => {
      TOAST_STATE.toasts = TOAST_STATE.toasts.map((toast) => 
        toast.id === id ? { ...toast, ...props } : toast
      )
      dispatch()
    }
  }
}

// 导出 Toaster 组件
export const Toaster = () => {
  const { toasts, dismiss } = useToast();
  
  return (
    <ToastProvider>
      {toasts.map(({ id, title, description, action, variant, open }) => (
        <Toast key={id} variant={variant} open={open}>
          <div className="grid gap-1">
            {title && <ToastTitle>{title}</ToastTitle>}
            {description && <ToastDescription>{description}</ToastDescription>}
          </div>
          {action}
          <ToastClose onClick={() => dismiss(id)} />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
};
