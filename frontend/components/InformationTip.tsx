
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { Info } from "lucide-react"
import type { ReactNode } from "react"

export function InformationTip({ content }: { content: ReactNode }) {
    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <button
                    type="button"
                    className="ml-1 inline-flex size-5 items-center justify-center align-middle text-[#9A9A9A] transition hover:text-[#7A7A7A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#CFCFCF]"
                    aria-label="Show information"
                >
                    <Info className="size-5" strokeWidth={1.6} />
                </button>
            </TooltipTrigger>
            <TooltipContent
                side="bottom"
                align="start"
                sideOffset={0}
                alignOffset={0}
                className="w-fit max-w-96 rounded-[3px] bg-[#F0F0F0] text-xs font-normal text-[#8A8A8A] shadow-none [&>svg]:hidden"
            >
                {typeof content === "string" ? <p>{content}</p> : content}
            </TooltipContent>
        </Tooltip>
    )
}
