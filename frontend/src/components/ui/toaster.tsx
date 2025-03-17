import * as React from "react"
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "./toast"
import { useToast } from "./use-toast"

interface ToastWithRequired {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  variant?: "default" | "destructive";
  open: boolean;
}

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <ToastProvider>
      {toasts.map((toast: ToastWithRequired) => (
        <Toast key={toast.id} variant={toast.variant} open={toast.open}>
          <div className="grid gap-1">
            {toast.title && <ToastTitle>{toast.title}</ToastTitle>}
            {toast.description && <ToastDescription>{toast.description}</ToastDescription>}
          </div>
          {toast.action}
          <ToastClose onClick={() => dismiss(toast.id)} />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  )
}
