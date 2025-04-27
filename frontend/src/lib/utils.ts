import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// 重新导出ScrollArea组件，帮助TypeScript识别它
export { ScrollArea } from "@/components/ui/scroll-area";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
