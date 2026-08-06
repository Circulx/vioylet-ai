"use client";

import { useMemo, useRef, useState } from "react";
import { Check, MessageSquarePlus, MoreVertical, PanelLeftClose, PanelLeftOpen, Pencil, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ChatSessionResponse } from "@/lib/api/contracts";
import { formatChatSessionDate } from "@/lib/chat-session-utils";
import { cn } from "@/lib/utils";

type ChatHistorySidebarProps = {
  sessions: ChatSessionResponse[];
  activeSessionId: string;
  isLoading?: boolean;
  isCreating?: boolean;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onRenameSession: (sessionId: string, title: string) => void;
  onDeleteSession: (sessionId: string) => void;
};

export default function ChatHistorySidebar({
  sessions,
  activeSessionId,
  isLoading = false,
  isCreating = false,
  onSelectSession,
  onNewChat,
  onRenameSession,
  onDeleteSession,
}: ChatHistorySidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState("");
  const [editingTitle, setEditingTitle] = useState("");
  const [pendingDeleteSession, setPendingDeleteSession] = useState<ChatSessionResponse | null>(null);
  const renameInFlightRef = useRef(false);

  const orderedSessions = useMemo(
    () =>
      [...sessions].sort(
        (left, right) =>
          new Date(right.updated_at || right.created_at).getTime() -
          new Date(left.updated_at || left.created_at).getTime(),
      ),
    [sessions],
  );

  const beginRename = (session: ChatSessionResponse) => {
    setEditingSessionId(session.id);
    setEditingTitle(session.title?.trim() || "Untitled chat");
  };

  const submitRename = () => {
    if (renameInFlightRef.current || !editingSessionId) {
      return;
    }
    const title = editingTitle.trim();
    setEditingSessionId("");
    setEditingTitle("");
    if (title) {
      renameInFlightRef.current = true;
      onRenameSession(editingSessionId, title);
      window.setTimeout(() => {
        renameInFlightRef.current = false;
      }, 300);
    }
  };

  if (isCollapsed) {
    return (
      <aside className="flex h-full w-12 shrink-0 flex-col border-r border-[#E5E5EA] bg-[#F8F9FC]">
        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          className="flex h-12 w-full items-center justify-center text-[#5F6372] hover:bg-[#EFF1F8]"
          aria-label="Show chat history"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onNewChat}
          disabled={isCreating}
          className="flex h-12 w-full items-center justify-center text-primary hover:bg-[#EFF1F8] disabled:opacity-50"
          aria-label="New chat"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>
      </aside>
    );
  }

  return (
    <>
      <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-[#E5E5EA] bg-[#F8F9FC]">
        <div className="flex items-center justify-between gap-2 border-b border-[#E5E5EA] px-3 py-3">
          <p className="text-sm font-semibold text-[#2F3342]">Chats</p>
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            className="flex h-8 w-8 items-center justify-center rounded-md text-[#5F6372] hover:bg-[#EFF1F8]"
            aria-label="Hide chat history"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>

        <div className="p-3">
          <button
            type="button"
            onClick={onNewChat}
            disabled={isCreating}
            className="flex w-full items-center gap-2 rounded-lg border border-[#DDE1EA] bg-white px-3 py-2.5 text-sm font-medium text-[#2F3342] shadow-sm transition hover:bg-[#F4F4F5] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <MessageSquarePlus className="h-4 w-4 text-primary" />
            New chat
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3 thin-scrollbar">
          {isLoading ? (
            <p className="px-2 py-4 text-xs text-[#8B8B94]">Loading chats...</p>
          ) : orderedSessions.length ? (
            <div className="space-y-1">
              {orderedSessions.map((session) => {
                const title = session.title?.trim() || "Untitled chat";
                const isActive = activeSessionId === session.id;
                const dateLabel = formatChatSessionDate(session.updated_at || session.created_at);

                return (
                  <div
                    key={session.id}
                    className={cn(
                      "group flex items-center gap-1 rounded-lg px-2 py-2 transition",
                      isActive ? "bg-white shadow-sm ring-1 ring-[#DDE1EA]" : "hover:bg-[#EFF1F8]",
                    )}
                  >
                    {editingSessionId === session.id ? (
                      <div className="relative min-w-0 flex-1">
                        <input
                          value={editingTitle}
                          onChange={(event) => setEditingTitle(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              submitRename();
                            }
                            if (event.key === "Escape") {
                              setEditingSessionId("");
                              setEditingTitle("");
                            }
                          }}
                          autoFocus
                          className="w-full rounded-md border border-[#DDE1EA] bg-white px-2 py-1 pr-8 text-sm text-[#2F3342] outline-none ring-1 ring-primary/20"
                        />
                        <button
                          type="button"
                          onClick={submitRename}
                          className="absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center text-primary"
                          aria-label="Save chat name"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => onSelectSession(session.id)}
                          className="min-w-0 flex-1 text-left"
                          title={title}
                        >
                          <p className="truncate text-sm font-medium text-[#2F3342]">{title}</p>
                          {dateLabel ? <p className="mt-0.5 text-[11px] text-[#8B8B94]">{dateLabel}</p> : null}
                        </button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              type="button"
                              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[#8B8B94] opacity-0 transition hover:bg-white group-hover:opacity-100 data-[state=open]:opacity-100"
                              aria-label={`Actions for ${title}`}
                            >
                              <MoreVertical className="h-4 w-4" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-36">
                            <DropdownMenuItem onClick={() => beginRename(session)}>
                              <Pencil className="h-4 w-4" />
                              Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem variant="destructive" onClick={() => setPendingDeleteSession(session)}>
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="px-2 py-4 text-xs leading-5 text-[#8B8B94]">
              No chats yet. Start a new chat — your conversations are saved here automatically.
            </p>
          )}
        </div>
      </aside>

      <AlertDialog open={Boolean(pendingDeleteSession)} onOpenChange={(open) => !open && setPendingDeleteSession(null)}>
        <AlertDialogContent className="max-w-[420px] rounded-none border-0 bg-white p-6 shadow-[0_20px_80px_-24px_rgba(15,23,42,0.35)]">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {pendingDeleteSession?.title?.trim() || "this chat"} and all its messages.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-none">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                if (pendingDeleteSession) {
                  onDeleteSession(pendingDeleteSession.id);
                  setPendingDeleteSession(null);
                }
              }}
              className="rounded-none bg-[#FF6D5E] text-white hover:bg-[#FF6D5E]/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
