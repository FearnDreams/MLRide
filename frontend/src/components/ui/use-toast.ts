import * as React from "react"
import { Toaster as InternalToaster } from "./toaster"
import {
  Toast,
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from "./toast"

const TOAST_LIMIT = 5

export interface ToastProps {
  id?: string
  title?: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  variant?: "default" | "destructive"
  open?: boolean
}

type ToastWithId = ToastProps & { 
  id: string; 
  open: boolean 
}

// 状态容器
const TOAST_STATE = {
  toasts: [] as ToastWithId[],
  listeners: new Set<() => void>(),
}

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

function dispatch() {
  TOAST_STATE.listeners.forEach((listener) => listener())
}

export function useToast() {
  const [toasts, setToasts] = React.useState<ToastWithId[]>(TOAST_STATE.toasts)
  
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

// 重新导出toast组件
export {
  InternalToaster as Toaster,
  Toast,
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
}