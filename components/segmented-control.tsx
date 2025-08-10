"use client"

import { useEffect, useId, useMemo } from "react"
import { cn } from "@/lib/utils"

type Option = {
  label: string
  value: string
  disabled?: boolean
}

export function SegmentedControl(props: {
  options: Option[]
  value?: string
  onChange?: (value: string) => void
  ariaLabel?: string
  size?: "sm" | "md"
}) {
  const { options, value, onChange, ariaLabel, size = "md" } = props
  const groupId = useId()

  const currentIndex = useMemo(() => options.findIndex((o) => o.value === value), [options, value])

  useEffect(() => {
    if (value === undefined && options.length > 0 && onChange) {
      onChange(options[0].value)
    }
  }, [options, onChange, value])

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn("inline-flex rounded-lg border bg-muted/30 p-1", size === "sm" ? "gap-1" : "gap-1.5")}
    >
      {options.map((opt, idx) => {
        const selected = opt.value === value
        return (
          <button
            key={opt.value}
            id={`${groupId}-${idx}`}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-disabled={opt.disabled || undefined}
            disabled={opt.disabled}
            onClick={() => onChange?.(opt.value)}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault()
                onChange?.(opt.value)
              }
              if (e.key === "ArrowRight" || e.key === "ArrowDown") {
                e.preventDefault()
                const next = (currentIndex + 1) % options.length
                onChange?.(options[next].value)
              }
              if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
                e.preventDefault()
                const prev = (currentIndex - 1 + options.length) % options.length
                onChange?.(options[prev].value)
              }
            }}
            className={cn(
              "min-w-10 select-none rounded-md px-3 py-1.5 text-sm font-medium outline-none transition-colors",
              selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-white/70",
            )}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
