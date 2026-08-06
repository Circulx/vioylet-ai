import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { ReactNode } from "react"

export function Tooltips({children, content, side, sideOffset, contentClassName}: {
    children: ReactNode,
    content?: string,
    side?: "top" | "right" | "bottom" | "left",
    sideOffset?: number,
    contentClassName?: string
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {children}
      </TooltipTrigger>
      <TooltipContent side={side} sideOffset={sideOffset} className={contentClassName}>
        {
            content &&  <p>{content}</p>
        }
      </TooltipContent>
    </Tooltip>
  )
}
