"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { addDays, format } from "date-fns"
import { Loader2, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
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
import type { WeatherRecordRead } from "@/lib/types"

const inputClass =
  "border-white/20 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-white/60"

interface SaveRecordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultLocation?: string
  /** Navigate to the new record's detail page after create. Defaults to false. */
  navigateOnSuccess?: boolean
}

export function SaveRecordDialog({
  open,
  onOpenChange,
  defaultLocation = "",
  navigateOnSuccess = false,
}: SaveRecordDialogProps) {
  const queryClient = useQueryClient()
  const router = useRouter()

  const today = format(new Date(), "yyyy-MM-dd")
  const [location, setLocation] = useState(defaultLocation)
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(format(addDays(new Date(), 4), "yyyy-MM-dd"))

  useEffect(() => {
    if (open) setLocation(defaultLocation)
  }, [open, defaultLocation])

  const mutation = useMutation({
    mutationFn: () => api.createRecord({ location, start_date: startDate, end_date: endDate }),
    onSuccess: (record: WeatherRecordRead) => {
      queryClient.invalidateQueries({ queryKey: ["records"] })
      toast.success("Record saved", {
        description: `${record.location.resolved_name} · ${record.readings.length} reading(s) stored.`,
      })
      onOpenChange(false)
      if (navigateOnSuccess) router.push(`/records/${record.id}`)
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : "Could not save the record."
      toast.error("Save failed", { description: message })
    },
  })

  const rangeInvalid = Boolean(startDate && endDate && endDate < startDate)
  const canSubmit = location.trim().length > 0 && startDate && endDate && !rangeInvalid && !mutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong border-white/20 text-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Save weather record</DialogTitle>
          <DialogDescription className="text-white/70">
            Store a snapshot for a location and date range (max 30 days). Only forecast days inside the range are
            stored.
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
            <Label htmlFor="record-location" className="text-white/80">
              Location
            </Label>
            <Input
              id="record-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="City, place, or zip"
              className={inputClass}
              autoComplete="off"
            />
          </div>

          <DateRangeFields
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
            idPrefix="create"
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
                  <Save className="h-4 w-4" /> Save record
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
