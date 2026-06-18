"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, ApiError } from "@/lib/api";
import type { ExportFormat } from "@/lib/types";

const FORMATS: { format: ExportFormat; label: string; ext: string }[] = [
  { format: "json", label: "JSON", ext: "json" },
  { format: "xml", label: "XML", ext: "xml" },
  { format: "csv", label: "CSV", ext: "csv" },
  { format: "markdown", label: "Markdown", ext: "md" },
  { format: "pdf", label: "PDF", ext: "pdf" },
];

function filenameFromDisposition(
  header: string | null,
  fallback: string,
): string {
  if (!header) return fallback;
  const match = /filename="?([^"]+)"?/.exec(header);
  return match?.[1] ?? fallback;
}

export function ExportMenu({ recordId }: { recordId: string }) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);

  async function handleExport(format: ExportFormat, ext: string) {
    setBusy(format);
    try {
      const res = await api.exportRecord(recordId, format);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filenameFromDisposition(
        res.headers.get("Content-Disposition"),
        `record-${recordId}.${ext}`,
      );
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Export failed. Please try again.";
      toast.error("Export failed", { description: message });
    } finally {
      setBusy(null);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="secondary"
            className="bg-white/15 text-white hover:bg-white/25"
            disabled={busy !== null}
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export
          </Button>
        }
      />
      <DropdownMenuContent
        align="end"
        className="glass-strong border-white/20 text-white"
      >
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-white/70">
            Download as
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-white/15" />
          {FORMATS.map((f) => (
            <DropdownMenuItem
              key={f.format}
              disabled={busy !== null}
              onClick={(e) => {
                e.preventDefault();
                handleExport(f.format, f.ext);
              }}
              className="cursor-pointer text-white focus:bg-white/15 focus:text-white"
            >
              {f.label}
              <span className="ml-auto text-xs text-white/50">.{f.ext}</span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
