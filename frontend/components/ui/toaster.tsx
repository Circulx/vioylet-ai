'use client'

import { useToast } from '@/components/ui/use-toast'
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  type ToastProps,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast'

function getToastDotClass(variant: ToastProps['variant']) {
  switch (variant) {
    case 'success':
      return 'bg-[#8FD9C9]'
    case 'warning':
      return 'bg-[#EBC37F]'
    case 'destructive':
      return 'bg-[#F1B2A3]'
    case 'default':
    case 'info':
    default:
      return 'bg-[#98C9F6]'
  }
}

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider duration={5000} swipeDirection="right">
      {toasts.map(function ({ id, title, description, action, variant, ...props }) {
        return (
          <Toast key={id} variant={variant} {...props}>
            <span
              aria-hidden="true"
              className={`mt-1.5 size-5 shrink-0 rounded-full ${getToastDotClass(variant)}`}
            />
            <div className="grid flex-1 gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
