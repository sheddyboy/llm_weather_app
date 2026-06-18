"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Save } from "lucide-react"
import { useEffect, useState } from "react"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { DateRangeFields } from "@/components/date-range-fields"
import { api, ApiError } from "@/lib/api"
import type { UpdateRecordInput, WeatherRecordRead } from "@/lib/types"

interface EditRecordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  record: WeatherRecordRead
}

export function EditRecordDialog({ open, onOpenChange, record }: EditRecordDialogProps) {
  const queryClient = useQueryClient()

  const [location, setLocation] = useState(record.location.resolved_name)
  const [startDate, setStartDate] = useState(record.start_date)
  const [endDate, setEndDate] = useState(record.end_date)

  // Reset fields to the current record whenever the dialog opens.
  useEffect(() => {
    if (open) {
      setLocation(record.location.resolved_name)
      setStartDate(record.start_date)
      setEndDate(record.end_date)
    }
  }, [open, record])

  const mutation = useMutation({
    mutationFn: () => {
      const payload: UpdateRecordInput = {}
      if (location.trim() && location.trim() !== record.location.resolved_name) payload.location = location.trim()
      if (startDate !== record.start_date) payload.start_date = startDate
      if (endDate !== record.end_date) payload.end_date = endDate
      return api.updateRecord(record.id, payload)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(["record", record.id], updated)
      queryClient.invalidateQueries({ queryKey: ["records"] })
      queryClient.invalidateQueries({ queryKey: ["record", record.id] })
      // Readings may have been refetched, so briefing/media derived data is stale.
      queryClient.invalidateQueries({ queryKey: ["briefing", record.id] })
      queryClient.invalidateQueries({ queryKey: ["media", record.id] })
      toast.success("Record updated")
      onOpenChange(false)
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : "Could not update the record."
      toast.error("Update failed", { description: message })
    },
  })

  const rangeInvalid = Boolean(startDate && endDate && endDate < startDate)
  const nothingChanged =
    location.trim() === record.location.resolved_name &&
    startDate === record.start_date &&
    endDate === record.end_date
  const canSubmit = location.trim().length > 0 && !rangeInvalid && !nothingChanged && !mutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong border-white/20 text-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit record</DialogTitle>
          <DialogDescription className="text-white/70">
            Changing the location or dates re-fetches the stored readings.
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (canSubmit) mutation.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="edit-location" className="text-white/80">
              Location
            </Label>
            <Input
              id="edit-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="City, place, or zip"
              className="border-white/20 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-white/60"
              autoComplete="off"
            />
          </div>

          <DateRangeFields
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
            idPrefix="edit"
          />

          {rangeInvalid && <p className="text-sm text-red-200">End date can&apos;t be before the start date.</p>}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="text-white/80 hover:bg-white/10 hover:text-white"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit} className="bg-white text-slate-900 hover:bg-white/90">
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Saving
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" /> Save changes
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
