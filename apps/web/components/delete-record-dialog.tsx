"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api, ApiError } from "@/lib/api"
import type { WeatherRecordRead } from "@/lib/types"

interface DeleteRecordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  recordId: string | null
  recordLabel?: string
  /** Called after a successful delete (e.g. to navigate away from a detail page). */
  onDeleted?: () => void
}

export function DeleteRecordDialog({
  open,
  onOpenChange,
  recordId,
  recordLabel,
  onDeleted,
}: DeleteRecordDialogProps) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (id: string) => api.deleteRecord(id),
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: ["records"] })
      const previous = queryClient.getQueriesData<WeatherRecordRead[]>({ queryKey: ["records"] })
      // Optimistically remove from every cached records list.
      queryClient.setQueriesData<WeatherRecordRead[]>({ queryKey: ["records"] }, (old) =>
        old ? old.filter((r) => r.id !== id) : old,
      )
      return { previous }
    },
    onError: (error, _id, context) => {
      context?.previous?.forEach(([key, value]) => queryClient.setQueryData(key, value))
      const message = error instanceof ApiError ? error.message : "Could not delete the record."
      toast.error("Delete failed", { description: message })
    },
    onSuccess: () => {
      toast.success("Record deleted")
      onOpenChange(false)
      onDeleted?.()
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["records"] })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong border-white/20 text-white sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete record?</DialogTitle>
          <DialogDescription className="text-white/70">
            {recordLabel ? (
              <>
                This will permanently delete the record for{" "}
                <span className="font-medium text-white">{recordLabel}</span> and its readings.
              </>
            ) : (
              "This will permanently delete this record and its readings."
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="text-white/80 hover:bg-white/10 hover:text-white"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!recordId || mutation.isPending}
            onClick={() => recordId && mutation.mutate(recordId)}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Deleting
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4" /> Delete
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
