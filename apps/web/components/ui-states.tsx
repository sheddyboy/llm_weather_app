import { AlertTriangle, type LucideIcon, Inbox } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api"

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown
  onRetry?: () => void
  className?: string
}) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Something went wrong. Please try again."

  return (
    <div className={`glass flex flex-col items-center gap-3 rounded-2xl p-8 text-center ${className ?? ""}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/20">
        <AlertTriangle className="h-6 w-6 text-red-200" aria-hidden="true" />
      </div>
      <p className="max-w-md text-balance text-sm text-white/80">{message}</p>
      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          className="bg-white/15 text-white hover:bg-white/25"
        >
          Try again
        </Button>
      )}
    </div>
  )
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={`glass flex flex-col items-center gap-3 rounded-2xl p-8 text-center ${className ?? ""}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10">
        <Icon className="h-6 w-6 text-white/70" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="font-medium text-white">{title}</p>
        {description && <p className="mx-auto max-w-md text-balance text-sm text-white/70">{description}</p>}
      </div>
      {action}
    </div>
  )
}
