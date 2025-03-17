import * as React from "react";

// 定义Toast类型
export type ToastType = {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  variant?: "default" | "destructive";
  action?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

// Toast状态管理
const TOAST_LIMIT = 5;
let count = 0;
const toasts: ToastType[] = [];
const listeners: Array<(toasts: ToastType[]) => void> = [];

const emitChange = () => {
  listeners.forEach((listener) => {
    listener([...toasts]);
  });
};

const addToast = (toast: Omit<ToastType, "id">) => {
  const id = String(++count);
  const newToast = { id, ...toast };
  
  // 添加到前面，限制数量
  toasts.unshift(newToast);
  if (toasts.length > TOAST_LIMIT) {
    toasts.pop();
  }
  
  emitChange();
  return id;
};

const dismissToast = (id: string) => {
  const index = toasts.findIndex((toast) => toast.id === id);
  if (index !== -1) {
    toasts.splice(index, 1);
    emitChange();
  }
};

const updateToast = (id: string, toast: Partial<ToastType>) => {
  const index = toasts.findIndex((t) => t.id === id);
  if (index !== -1) {
    toasts[index] = { ...toasts[index], ...toast };
    emitChange();
  }
};

// 导出的toast函数
export const toast = {
  success: (title: string, description?: string) => {
    return addToast({
      variant: "default",
      title,
      description,
    });
  },
  error: (title: string, description?: string) => {
    return addToast({
      variant: "destructive",
      title,
      description,
    });
  },
  custom: (props: Omit<ToastType, "id">) => {
    const id = addToast(props);
    return {
      id,
      dismiss: () => dismissToast(id),
      update: (props: Partial<Omit<ToastType, "id">>) => updateToast(id, props),
    };
  },
  dismiss: (id: string) => {
    dismissToast(id);
  },
};

// 导出一个注册监听器的函数用于Toaster组件
export function useToasts() {
  const [stateToasts, setStateToasts] = React.useState<ToastType[]>([]);
  
  React.useEffect(() => {
    const handleChange = (updatedToasts: ToastType[]) => {
      setStateToasts(updatedToasts);
    };
    
    listeners.push(handleChange);
    setStateToasts([...toasts]); // 初始状态
    
    return () => {
      const index = listeners.indexOf(handleChange);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  }, []);
  
  return stateToasts;
}
